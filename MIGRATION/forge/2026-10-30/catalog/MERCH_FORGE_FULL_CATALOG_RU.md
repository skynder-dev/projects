# MERCH FORGE — полный каталог ниш и концепций

Снимок: 30 октября 2026, 16:02:51 UTC. Источник: read-only Supabase, схема `merch`, проект `media-business-projects`.

**48 ниш · 174 записи концептов · 167 концептов после семантического дедупа · 7 исторических дублей.** Все исходные записи сохранены.

## Даты и полнота ревизий

Дополнительно восстановлены 174 записи `concept_revisions`: все №1 initial, созданы 25 сентября 2026. 174 current_revision_id проверены; 10 production specs заполнены, 164 пусты. Полные тексты ревизий и метаданные — в JSON; читаемые спецификации — `MERCH_FORGE_REVISIONS_RU.md`.

Canonical concepts в БД последний раз обновлялись **24 сентября 2026**, хотя чтение выполнено 30 октября. Это не подтверждение синхронизации с PC и не полный backup Forge. Среди 50 V4: 10 финалистов, 9 editorial demoted, 31 research_bank_not_promoted (не отказ владельца).

## Как читать статусы

- `scored` и `shortlisted` — состояние исследовательского отбора, не одобрение владельца.
- Все поля `user_decision` пусты; в `concept_acceptances` 0 записей. Исторические отказы отдельно отражены в metadata и имеют приоритет перед старым `scored`.
- 15 старых концепций сняты после owner review. 10 V4-финалистов — другой список; их нельзя считать теми же 15 или автоматически одобренными.
- Баллы, confidence и evidence приведены как сохраненная исследовательская оценка. Это не продажи, не правовое заключение и не заново проверенные рынки.
- Полные вложенные metadata, provenance, источники, дата каждого score и визуальные спецификации доступны в `MERCH_FORGE_FULL_CATALOG.json`.

## Модель оценки: текущий снимок

| Область | Измерение | Вес | Описание |
|---|---|---:|---|
| concept | buyer_desire | 30.00 | Would a real buyer pay to wear or gift this exact idea because of a concrete emotional/social trigger? Mere recognition of job vocabulary scores low. |
| concept | clarity_at_glance | 8.00 | Can a viewer quickly understand the human premise or punchline, not merely parse technical steps? |
| concept | distinctiveness | 15.00 | Is there an original point of view, joke, situation, identity signal or visual premise? Rare jargon by itself is not distinctiveness. |
| concept | giftability | 10.00 | Is there a plausible recipient/occasion and a reason a giver would choose this exact idea over generic profession merch? |
| concept | insider_resonance | 15.00 | Does it capture a shared situation, frustration, pride point, ritual or truth insiders recognize? Jargon density alone does not count. |
| concept | ip_safety | 5.00 | Can the exact premise, wording and visual be executed without protected brands, slogans, characters, copied graphics or misleading claims? |
| concept | niche_fit | 5.00 | Does the concept genuinely belong to this audience without depending on job-title labeling or vocabulary lists? |
| concept | visual_potential | 12.00 | Can the human idea become a strong apparel composition rather than a diagram, checklist or training graphic? |
| niche | channel_breadth | 5.00 | Usefulness beyond one marketplace/channel and fit with broader Town Label commerce/content. |
| niche | competition_opportunity | 15.00 | Room for differentiated offers; higher means less commoditized/copycat pressure relative to demand. |
| niche | concept_depth | 12.00 | How many materially different authentic hooks can be developed without repeating the same joke/text. |
| niche | demand_evidence | 20.00 | Evidence that a real buyer population actively searches, buys, gifts or identifies with this niche. |
| niche | founder_edge | 2.00 | Advantage from first-hand knowledge, access, community understanding or easier validation. |
| niche | identity_intensity | 15.00 | How strongly people self-identify with the niche and enjoy signaling membership. |
| niche | legal_safety | 3.00 | Relative ability to create without leaning on protected brands, logos, characters or risky claims. |
| niche | purchase_motivation | 15.00 | Strength of plausible reasons to buy beyond generic job-title decoration. |
| niche | repeatability | 5.00 | Ability to support a series, variants, seasons, gifts or repeat purchase. |
| niche | visual_language | 8.00 | Availability of recognizable symbols, tools, situations, environments and insider cues for strong art. |

Внимание: текущие веса обновлялись; старые агрегаты могут относиться к иной модели. Не пересчитывать историческую и текущую очередь как одну сопоставимую шкалу.

## Семантический дедуп

- `avionics_power_signal_data_ground` → `avionics_power_ground_signal_data_v2`. Same four core domains POWER/SIGNAL/DATA/GROUND; v2 has the stronger score and equivalent concept substance. Статус основной записи: Исследовательский кандидат; одобрение владельца не зафиксировано.
- `cyto_cell_nucleus_pattern_abnormality` → `cyto_cell_nucleus_morphology_pattern`. Same core cell/nucleus/pattern morphology-analysis concept; existing concept is stronger and cleaner. Статус основной записи: Исторический: снят после owner review; не возвращать автоматически.
- `cyto_pap_fna_fluid_slide` → `cyto_pap_fna_body_fluids`. Same PAP/FNA/body-fluid specimen-family hook; challenger only adds generic SLIDE. Статус основной записи: Исследовательский кандидат; одобрение владельца не зафиксировано.
- `cyto_prep_stain_screen_report` → `cyto_stain_screen_identify_report`. Same cytology preparation/stain/screen/report workflow; existing concept is stronger and adds identification. Статус основной записи: Исторический: снят после owner review; не возвращать автоматически.
- `eet_prototype_assemble_test_troubleshoot` → `eet_build_test_troubleshoot_document`. Same build/assemble + test + troubleshoot workflow; challenger scores higher and adds documentation. Статус основной записи: Исследовательский кандидат; одобрение владельца не зафиксировано.
- `oph_iop_field_acuity_refraction` → `ophth_acuity_pressure_refraction`. Same core ophthalmic diagnostic-domain list; IOP is pressure and FIELD is incremental, not a materially new buyer hook. Статус основной записи: Исследовательский кандидат; одобрение владельца не зафиксировано.
- `oph_measure_record_verify_assist` → `ophth_tonometry_measure_record`. Generic measure/record workflow materially overlaps the stronger tonometry-specific measurement concept. Статус основной записи: Исторический: снят после owner review; не возвращать автоматически.

## Исторический пакет F01–F15: снят после owner review

Не смешивать с 10 V4-финалистами. Идентификаторы F взяты из исторической таблицы разговора и сверены с хуками живого каталога.

- **F01** `ophth_tonometry_measure_record` — PRESSURE • MEASURE • RECORD
- **F02** `industrial_machine_systems` — MACHINE SYSTEMS | MOTORS • CONVEYORS • DRIVES
- **F03** `sterile_processing_one_way_workflow` — SOILED → CLEAN → STERILE
- **F04** `cyto_cell_nucleus_morphology_pattern` — CELL • NUCLEUS • MORPHOLOGY • PATTERN
- **F05** `eet_schematic_board_signal_path` — SCHEMATIC → BOARD → SIGNAL
- **F06** `avionics_fault_isolate_lru` — FAULT → ISOLATE → LRU → VERIFY
- **F07** `cyto_stain_screen_identify_report` — STAIN • SCREEN • IDENTIFY • REPORT
- **F08** `bmet_service_call_test_fix_verify` — SYMPTOM → TEST → FIX → VERIFY
- **F09** `ic_loop_check_zero_span` — LOOP CHECK • ZERO • SPAN
- **F10** `ophth_visual_field_map` — FIELD • MAP • REVIEW
- **F11** `relay_ct_pt_logic_trip_chain` — CT/PT → RELAY → LOGIC → TRIP
- **F12** `relay_fault_trip_breaker_path` — FAULT → RELAY → TRIP → BREAKER
- **F13** `spd_count_inspect_verify_release` — COUNT • INSPECT • VERIFY • RELEASE
- **F14** `avionics_pin_to_pin_trace` — PIN → WIRE → CONNECTOR → PIN
- **F15** `semi_wafer_lot_tool_metrology` — WAFER • LOT • TOOL • METROLOGY

## Все 48 ниш и связанные концепции

## 01. Avionics Technician
Ключ: `avionics_technician` · ID: `6cf6c633-d812-4049-bc1a-59c33e5feb88`

**Статус БД:** shortlisted · **балл:** 81.40 · **confidence:** 71.00 · **coverage:** 100.00
**Аудитория:** Aircraft avionics technicians, maintainers and electronics specialists
**Категория:** occupational_identity
**Исследовательская аргументация:** Technically rich aviation-maintenance identity with wiring, boxes, troubleshooting and test-equipment language; current Etsy samples exist but appear materially narrower than generic aircraft-mechanic merch.
**Создано / обновлено:** 2026-09-23 09:34:00.70472+00 / 2026-09-23 10:03:30.159451+00

### Компоненты оценки ниши

- **channel_breadth**: 7.50 (confidence 0.600). Initial evidence-weighted Forge score from current BLS/O*NET data, sampled Etsy competition and practitioner-community signals. See niche_candidates.source_notes. This is prioritization research, not a sales forecast. Дата: 2026-09-23 09:34:30.438105+00.
- **competition_opportunity**: 7.50 (confidence 0.600). Initial evidence-weighted Forge score from current BLS/O*NET data, sampled Etsy competition and practitioner-community signals. See niche_candidates.source_notes. This is prioritization research, not a sales forecast. Дата: 2026-09-23 09:34:30.438105+00.
- **concept_depth**: 9.50 (confidence 0.750). Initial evidence-weighted Forge score from current BLS/O*NET data, sampled Etsy competition and practitioner-community signals. See niche_candidates.source_notes. This is prioritization research, not a sales forecast. Дата: 2026-09-23 09:34:30.438105+00.
- **demand_evidence**: 8.00 (confidence 0.800). Initial evidence-weighted Forge score from current BLS/O*NET data, sampled Etsy competition and practitioner-community signals. See niche_candidates.source_notes. This is prioritization research, not a sales forecast. Дата: 2026-09-23 09:34:30.438105+00.
- **founder_edge**: 2.00 (confidence 0.400). Initial evidence-weighted Forge score from current BLS/O*NET data, sampled Etsy competition and practitioner-community signals. See niche_candidates.source_notes. This is prioritization research, not a sales forecast. Дата: 2026-09-23 09:34:30.438105+00.
- **identity_intensity**: 8.50 (confidence 0.750). Initial evidence-weighted Forge score from current BLS/O*NET data, sampled Etsy competition and practitioner-community signals. See niche_candidates.source_notes. This is prioritization research, not a sales forecast. Дата: 2026-09-23 09:34:30.438105+00.
- **legal_safety**: 7.50 (confidence 0.600). Initial evidence-weighted Forge score from current BLS/O*NET data, sampled Etsy competition and practitioner-community signals. See niche_candidates.source_notes. This is prioritization research, not a sales forecast. Дата: 2026-09-23 09:34:30.438105+00.
- **purchase_motivation**: 8.00 (confidence 0.700). Initial evidence-weighted Forge score from current BLS/O*NET data, sampled Etsy competition and practitioner-community signals. See niche_candidates.source_notes. This is prioritization research, not a sales forecast. Дата: 2026-09-23 09:34:30.438105+00.
- **repeatability**: 8.00 (confidence 0.650). Initial evidence-weighted Forge score from current BLS/O*NET data, sampled Etsy competition and practitioner-community signals. See niche_candidates.source_notes. This is prioritization research, not a sales forecast. Дата: 2026-09-23 09:34:30.438105+00.
- **visual_language**: 9.50 (confidence 0.800). Initial evidence-weighted Forge score from current BLS/O*NET data, sampled Etsy competition and practitioner-community signals. See niche_candidates.source_notes. This is prioritization research, not a sales forecast. Дата: 2026-09-23 09:34:30.438105+00.

### Концепции (14)

#### Avionics — bench test waveform
`avionics_bench_test_waveform` · ID `a064d00b-5686-407a-a92a-146d8ca4ff4c`

**Интерпретация:** Исследовательский кандидат; одобрение владельца не зафиксировано
**Статус БД:** scored · **балл:** 88.25 · **confidence:** 68.17 · **coverage:** 100.00
**Текст / хук:** BENCH TEST • SIGNAL • VERIFY
**Идея:** Avionics — bench test waveform. Core hook: BENCH TEST • SIGNAL • VERIFY. Electrical/electronic aircraft-system troubleshooting without aircraft/OEM branding. Execution must stay original and descriptive; avoid employer, OEM, certification-body, association and proprietary-interface branding.
**Покупатель:** Aircraft avionics technicians and maintainers
**Причина покупки:** Identity purchase for aircraft avionics technicians and maintainers who recognize the real workflow/systems language.
**Отличие:** Insider technical technical map direction intended to avoid generic profession-title, retro-badge, skull, flag, coffee and parody templates.
**Визуальное направление:** Generic electronics bench, module and original waveform/test-point composition.
**Создано / обновлено:** 2026-09-23 09:48:50.541446+00 / 2026-09-23 09:55:40.114238+00

Компоненты оценки:
- **buyer_desire**: 8.39 (confidence 0.670). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **clarity_at_glance**: 7.77 (confidence 0.670). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **distinctiveness**: 9.20 (confidence 0.670). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **giftability**: 7.47 (confidence 0.670). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **insider_resonance**: 9.30 (confidence 0.700). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **ip_safety**: 8.60 (confidence 0.670). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **niche_fit**: 9.37 (confidence 0.700). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **visual_potential**: 9.60 (confidence 0.700). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.

#### Avionics — fault isolate / LRU
`avionics_fault_isolate_lru` · ID `b1ec1e4d-3846-4288-b92a-a6eb37564893`

**Интерпретация:** Исторический: снят после owner review; не возвращать автоматически
**Статус БД:** scored · **балл:** 89.44 · **confidence:** 69.17 · **coverage:** 100.00
**Текст / хук:** FAULT → ISOLATE → LRU → VERIFY
**Идея:** Avionics — fault isolate / LRU. Core hook: FAULT → ISOLATE → LRU → VERIFY. Electrical/electronic aircraft-system troubleshooting without aircraft/OEM branding. Execution must stay original and descriptive; avoid employer, OEM, certification-body, association and proprietary-interface branding.
**Покупатель:** Aircraft avionics technicians and maintainers
**Причина покупки:** Identity purchase for aircraft avionics technicians and maintainers who recognize the real workflow/systems language.
**Отличие:** Insider technical diagnostic direction intended to avoid generic profession-title, retro-badge, skull, flag, coffee and parody templates.
**Визуальное направление:** Troubleshooting chain from symptom to generic line-replaceable unit and verification.
**retired_reason:** failed purchase-trigger quality bar after owner review
**Создано / обновлено:** 2026-09-23 09:48:50.541446+00 / 2026-09-23 23:40:31.847823+00

Компоненты оценки:
- **buyer_desire**: 8.79 (confidence 0.680). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **clarity_at_glance**: 8.60 (confidence 0.680). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **distinctiveness**: 9.10 (confidence 0.680). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **giftability**: 7.90 (confidence 0.680). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **insider_resonance**: 9.45 (confidence 0.710). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **ip_safety**: 8.70 (confidence 0.680). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **niche_fit**: 9.47 (confidence 0.710). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **visual_potential**: 8.95 (confidence 0.710). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.

#### Avionics — LRU service loop
`avionics_lru_remove_test_replace_verify` · ID `e7e87078-6c0c-4ad6-967a-8b09da04bb5c`

**Интерпретация:** Исследовательский кандидат; одобрение владельца не зафиксировано
**Статус БД:** scored · **балл:** 83.30 · **confidence:** 64.78 · **coverage:** 100.00
**Текст / хук:** REMOVE • TEST • REPLACE • VERIFY
**Идея:** AVIONICS TECHNICIAN with a generic LRU-style electronics box and the service loop REMOVE • TEST • REPLACE • VERIFY. Keep the hardware generic and original; the point is the maintenance workflow, not a specific aircraft part number or manufacturer.
**Покупатель:** Aircraft avionics technicians and maintainers
**Причина покупки:** Insider maintenance workflow with strong gift/identity value.
**Отличие:** Uses the replaceable-module workflow rather than pilot/aircraft imagery.
**Визуальное направление:** Exploded generic electronics module, connector blocks, arrows and test meter motifs
**Создано / обновлено:** 2026-09-23 09:36:02.928333+00 / 2026-09-23 10:09:42.905504+00

Компоненты оценки:
- **buyer_desire**: 7.50 (confidence 0.600). Initial Forge concept score using current occupational terminology, sampled marketplace patterns and technical distinctiveness. No visual has been generated; exact phrases still require IP/common-law screening before promotion. Дата: 2026-09-23 09:36:38.256823+00.
- **clarity_at_glance**: 7.50 (confidence 0.580). Initial Forge concept score using current occupational terminology, sampled marketplace patterns and technical distinctiveness. No visual has been generated; exact phrases still require IP/common-law screening before promotion. Дата: 2026-09-23 09:36:38.256823+00.
- **distinctiveness**: 9.00 (confidence 0.660). Initial Forge concept score using current occupational terminology, sampled marketplace patterns and technical distinctiveness. No visual has been generated; exact phrases still require IP/common-law screening before promotion. Дата: 2026-09-23 09:36:38.256823+00.
- **giftability**: 7.00 (confidence 0.550). Initial Forge concept score using current occupational terminology, sampled marketplace patterns and technical distinctiveness. No visual has been generated; exact phrases still require IP/common-law screening before promotion. Дата: 2026-09-23 09:36:38.256823+00.
- **insider_resonance**: 9.00 (confidence 0.720). Initial Forge concept score using current occupational terminology, sampled marketplace patterns and technical distinctiveness. No visual has been generated; exact phrases still require IP/common-law screening before promotion. Дата: 2026-09-23 09:36:38.256823+00.
- **ip_safety**: 8.50 (confidence 0.600). Initial Forge concept score using current occupational terminology, sampled marketplace patterns and technical distinctiveness. No visual has been generated; exact phrases still require IP/common-law screening before promotion. Дата: 2026-09-23 09:36:38.256823+00.
- **niche_fit**: 9.50 (confidence 0.740). Initial Forge concept score using current occupational terminology, sampled marketplace patterns and technical distinctiveness. No visual has been generated; exact phrases still require IP/common-law screening before promotion. Дата: 2026-09-23 09:36:38.256823+00.
- **visual_potential**: 8.50 (confidence 0.680). Initial Forge concept score using current occupational terminology, sampled marketplace patterns and technical distinctiveness. No visual has been generated; exact phrases still require IP/common-law screening before promotion. Дата: 2026-09-23 09:36:38.256823+00.

#### Avionics — pin-to-pin trace
`avionics_pin_to_pin_trace` · ID `51c1c1bc-29e0-4bf6-9d0d-2c7cd6a8f93b`

**Интерпретация:** Исторический: снят после owner review; не возвращать автоматически
**Статус БД:** scored · **балл:** 88.86 · **confidence:** 68.17 · **coverage:** 100.00
**Текст / хук:** PIN → WIRE → CONNECTOR → PIN
**Идея:** Avionics — pin-to-pin trace. Core hook: PIN → WIRE → CONNECTOR → PIN. Electrical/electronic aircraft-system troubleshooting without aircraft/OEM branding. Execution must stay original and descriptive; avoid employer, OEM, certification-body, association and proprietary-interface branding.
**Покупатель:** Aircraft avionics technicians and maintainers
**Причина покупки:** Identity purchase for aircraft avionics technicians and maintainers who recognize the real workflow/systems language.
**Отличие:** Insider technical technical map direction intended to avoid generic profession-title, retro-badge, skull, flag, coffee and parody templates.
**Визуальное направление:** Original wiring-path composition with generic connector pins and continuity trace; no aircraft/OEM wiring diagram copied.
**retired_reason:** failed purchase-trigger quality bar after owner review
**Создано / обновлено:** 2026-09-23 09:48:50.541446+00 / 2026-09-23 23:40:31.847823+00

Компоненты оценки:
- **buyer_desire**: 8.49 (confidence 0.670). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **clarity_at_glance**: 7.80 (confidence 0.670). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **distinctiveness**: 9.30 (confidence 0.670). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **giftability**: 7.50 (confidence 0.670). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **insider_resonance**: 9.35 (confidence 0.700). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **ip_safety**: 8.60 (confidence 0.670). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **niche_fit**: 9.37 (confidence 0.700). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **visual_potential**: 9.65 (confidence 0.700). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.

#### Avionics — power / ground / signal / data
`avionics_power_ground_signal_data_v2` · ID `b509d5e1-8120-441a-bf7c-3aed3801e3d4`

**Интерпретация:** Исследовательский кандидат; одобрение владельца не зафиксировано
**Статус БД:** scored · **балл:** 88.25 · **confidence:** 69.17 · **coverage:** 100.00
**Текст / хук:** POWER • GROUND • SIGNAL • DATA
**Идея:** Avionics — power / ground / signal / data. Core hook: POWER • GROUND • SIGNAL • DATA. Electrical/electronic aircraft-system troubleshooting without aircraft/OEM branding. Execution must stay original and descriptive; avoid employer, OEM, certification-body, association and proprietary-interface branding.
**Покупатель:** Aircraft avionics technicians and maintainers
**Причина покупки:** Identity purchase for aircraft avionics technicians and maintainers who recognize the real workflow/systems language.
**Отличие:** Insider technical system map direction intended to avoid generic profession-title, retro-badge, skull, flag, coffee and parody templates.
**Визуальное направление:** Four diagnostic domains arranged around a generic avionics module and test points.
**Создано / обновлено:** 2026-09-23 09:48:50.541446+00 / 2026-09-23 10:05:50.016716+00

Компоненты оценки:
- **buyer_desire**: 8.49 (confidence 0.680). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **clarity_at_glance**: 8.17 (confidence 0.680). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **distinctiveness**: 9.00 (confidence 0.680). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **giftability**: 7.57 (confidence 0.680). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **insider_resonance**: 9.10 (confidence 0.710). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **ip_safety**: 8.80 (confidence 0.680). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **niche_fit**: 9.37 (confidence 0.710). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **visual_potential**: 9.60 (confidence 0.710). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.

#### Avionics — power / signal / data / ground
`avionics_power_signal_data_ground` · ID `8182ee63-d30e-49e1-94f2-00123d7524ed`

**Интерпретация:** Исторический: семантический дубликат
**Статус БД:** paused · **балл:** 84.54 · **confidence:** 65.54 · **coverage:** 100.00
**Текст / хук:** POWER • SIGNAL • DATA • GROUND
**Идея:** AVIONICS TECHNICIAN technical composition using POWER • SIGNAL • DATA • GROUND as four diagnostic domains, supported by an original circuit/wiring schematic and generic test-instrument symbols.
**Покупатель:** Aircraft avionics technicians and maintainers
**Причина покупки:** Compact insider language that reads quickly and supports technical pride.
**Отличие:** Abstract diagnostic system rather than a copied aircraft diagram.
**Визуальное направление:** Four-quadrant or signal-bus layout with test points and meter/waveform marks
**semantic_duplicate_of:** avionics_power_ground_signal_data_v2
**semantic_duplicate_reason:** Same four core domains POWER/SIGNAL/DATA/GROUND; v2 has the stronger score and equivalent concept substance.
**Создано / обновлено:** 2026-09-23 09:36:02.928333+00 / 2026-09-23 10:09:42.905504+00

Компоненты оценки:
- **buyer_desire**: 8.00 (confidence 0.640). Initial Forge concept score using current occupational terminology, sampled marketplace patterns and technical distinctiveness. No visual has been generated; exact phrases still require IP/common-law screening before promotion. Дата: 2026-09-23 09:36:38.256823+00.
- **clarity_at_glance**: 8.50 (confidence 0.660). Initial Forge concept score using current occupational terminology, sampled marketplace patterns and technical distinctiveness. No visual has been generated; exact phrases still require IP/common-law screening before promotion. Дата: 2026-09-23 09:36:38.256823+00.
- **distinctiveness**: 8.50 (confidence 0.620). Initial Forge concept score using current occupational terminology, sampled marketplace patterns and technical distinctiveness. No visual has been generated; exact phrases still require IP/common-law screening before promotion. Дата: 2026-09-23 09:36:38.256823+00.
- **giftability**: 7.50 (confidence 0.580). Initial Forge concept score using current occupational terminology, sampled marketplace patterns and technical distinctiveness. No visual has been generated; exact phrases still require IP/common-law screening before promotion. Дата: 2026-09-23 09:36:38.256823+00.
- **insider_resonance**: 8.50 (confidence 0.680). Initial Forge concept score using current occupational terminology, sampled marketplace patterns and technical distinctiveness. No visual has been generated; exact phrases still require IP/common-law screening before promotion. Дата: 2026-09-23 09:36:38.256823+00.
- **ip_safety**: 9.00 (confidence 0.660). Initial Forge concept score using current occupational terminology, sampled marketplace patterns and technical distinctiveness. No visual has been generated; exact phrases still require IP/common-law screening before promotion. Дата: 2026-09-23 09:36:38.256823+00.
- **niche_fit**: 9.20 (confidence 0.720). Initial Forge concept score using current occupational terminology, sampled marketplace patterns and technical distinctiveness. No visual has been generated; exact phrases still require IP/common-law screening before promotion. Дата: 2026-09-23 09:36:38.256823+00.
- **visual_potential**: 9.00 (confidence 0.700). Initial Forge concept score using current occupational terminology, sampled marketplace patterns and technical distinctiveness. No visual has been generated; exact phrases still require IP/common-law screening before promotion. Дата: 2026-09-23 09:36:38.256823+00.

#### Avionics — remove / install / operational check
`avionics_remove_install_operational_check` · ID `b122d487-4501-43d4-9bbd-8275895d2696`

**Интерпретация:** Исследовательский кандидат; одобрение владельца не зафиксировано
**Статус БД:** scored · **балл:** 85.12 · **confidence:** 67.17 · **coverage:** 100.00
**Текст / хук:** REMOVE • INSTALL • CHECK • RELEASE
**Идея:** Avionics — remove / install / operational check. Core hook: REMOVE • INSTALL • CHECK • RELEASE. Electrical/electronic aircraft-system troubleshooting without aircraft/OEM branding. Execution must stay original and descriptive; avoid employer, OEM, certification-body, association and proprietary-interface branding.
**Покупатель:** Aircraft avionics technicians and maintainers
**Причина покупки:** Identity purchase for aircraft avionics technicians and maintainers who recognize the real workflow/systems language.
**Отличие:** Insider technical workflow direction intended to avoid generic profession-title, retro-badge, skull, flag, coffee and parody templates.
**Визуальное направление:** Generic replaceable-module service loop with connector and rack geometry; no aircraft model or part number.
**Создано / обновлено:** 2026-09-23 09:48:50.541446+00 / 2026-09-23 09:55:40.114238+00

Компоненты оценки:
- **buyer_desire**: 8.19 (confidence 0.660). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **clarity_at_glance**: 9.13 (confidence 0.660). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **distinctiveness**: 8.30 (confidence 0.660). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **giftability**: 8.03 (confidence 0.660). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **insider_resonance**: 8.75 (confidence 0.690). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **ip_safety**: 9.00 (confidence 0.660). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **niche_fit**: 9.27 (confidence 0.690). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **visual_potential**: 8.35 (confidence 0.690). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.

#### Avionics — signal path troubleshooting
`avionics_signal_path_trace_test_isolate_verify` · ID `d3c50125-284d-410d-b1c5-0f79a2739875`

**Интерпретация:** Исследовательский кандидат; одобрение владельца не зафиксировано
**Статус БД:** scored · **балл:** 86.26 · **confidence:** 67.97 · **coverage:** 100.00
**Текст / хук:** TRACE • TEST • ISOLATE • VERIFY
**Идея:** AVIONICS TECHNICIAN identity built around TRACE • TEST • ISOLATE • VERIFY. Show an original abstract signal path connecting power, wiring/data bus, a generic replaceable electronics module, sensor input and cockpit/display output. No aircraft manufacturer, airline, military-unit or model branding.
**Покупатель:** Aircraft avionics technicians and maintainers
**Причина покупки:** Signals technical competence rather than generic airplane fandom.
**Отличие:** Technical troubleshooting hierarchy instead of aircraft silhouette, wings, flags or generic mechanic jokes.
**Визуальное направление:** Clean wiring/signal-flow schematic; connector pins, test points, waveform accents; highly legible at shirt scale
**Создано / обновлено:** 2026-09-23 09:36:02.928333+00 / 2026-09-23 10:09:42.905504+00

Компоненты оценки:
- **buyer_desire**: 8.20 (confidence 0.680). Initial Forge concept score using current occupational terminology, sampled marketplace patterns and technical distinctiveness. No visual has been generated; exact phrases still require IP/common-law screening before promotion. Дата: 2026-09-23 09:36:38.256823+00.
- **clarity_at_glance**: 8.00 (confidence 0.640). Initial Forge concept score using current occupational terminology, sampled marketplace patterns and technical distinctiveness. No visual has been generated; exact phrases still require IP/common-law screening before promotion. Дата: 2026-09-23 09:36:38.256823+00.
- **distinctiveness**: 8.80 (confidence 0.650). Initial Forge concept score using current occupational terminology, sampled marketplace patterns and technical distinctiveness. No visual has been generated; exact phrases still require IP/common-law screening before promotion. Дата: 2026-09-23 09:36:38.256823+00.
- **giftability**: 7.50 (confidence 0.600). Initial Forge concept score using current occupational terminology, sampled marketplace patterns and technical distinctiveness. No visual has been generated; exact phrases still require IP/common-law screening before promotion. Дата: 2026-09-23 09:36:38.256823+00.
- **insider_resonance**: 9.00 (confidence 0.720). Initial Forge concept score using current occupational terminology, sampled marketplace patterns and technical distinctiveness. No visual has been generated; exact phrases still require IP/common-law screening before promotion. Дата: 2026-09-23 09:36:38.256823+00.
- **ip_safety**: 8.50 (confidence 0.620). Initial Forge concept score using current occupational terminology, sampled marketplace patterns and technical distinctiveness. No visual has been generated; exact phrases still require IP/common-law screening before promotion. Дата: 2026-09-23 09:36:38.256823+00.
- **niche_fit**: 9.50 (confidence 0.750). Initial Forge concept score using current occupational terminology, sampled marketplace patterns and technical distinctiveness. No visual has been generated; exact phrases still require IP/common-law screening before promotion. Дата: 2026-09-23 09:36:38.256823+00.
- **visual_potential**: 9.20 (confidence 0.720). Initial Forge concept score using current occupational terminology, sampled marketplace patterns and technical distinctiveness. No visual has been generated; exact phrases still require IP/common-law screening before promotion. Дата: 2026-09-23 09:36:38.256823+00.

#### Avionics — wiring / connector / continuity
`avionics_wiring_connector_continuity` · ID `ef82132d-4902-4909-b9fa-a5ecbae5545c`

**Интерпретация:** Исследовательский кандидат; одобрение владельца не зафиксировано
**Статус БД:** scored · **балл:** 87.63 · **confidence:** 68.17 · **coverage:** 100.00
**Текст / хук:** WIRING • CONNECTOR • CONTINUITY
**Идея:** Avionics — wiring / connector / continuity. Core hook: WIRING • CONNECTOR • CONTINUITY. Electrical/electronic aircraft-system troubleshooting without aircraft/OEM branding. Execution must stay original and descriptive; avoid employer, OEM, certification-body, association and proprietary-interface branding.
**Покупатель:** Aircraft avionics technicians and maintainers
**Причина покупки:** Identity purchase for aircraft avionics technicians and maintainers who recognize the real workflow/systems language.
**Отличие:** Insider technical technical map direction intended to avoid generic profession-title, retro-badge, skull, flag, coffee and parody templates.
**Визуальное направление:** Technical connector-pin field with continuity path and meter/waveform motifs.
**Создано / обновлено:** 2026-09-23 09:48:50.541446+00 / 2026-09-23 09:55:40.114238+00

Компоненты оценки:
- **buyer_desire**: 8.29 (confidence 0.670). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **clarity_at_glance**: 7.73 (confidence 0.670). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **distinctiveness**: 9.10 (confidence 0.670). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **giftability**: 7.43 (confidence 0.670). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **insider_resonance**: 9.25 (confidence 0.700). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **ip_safety**: 8.60 (confidence 0.670). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **niche_fit**: 9.37 (confidence 0.700). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **visual_potential**: 9.55 (confidence 0.700). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.

#### Avionics — technician black cloud
`v4_av_black_cloud` · ID `9698bf0f-002e-4902-a171-6364c310f708`

**Интерпретация:** V4: редакционный финалист на выбор владельца, НЕ подтвержденное одобрение
**Статус БД:** shortlisted · **балл:** 87.87 · **confidence:** 70.32 · **coverage:** 100.00
**Текст / хук:** I DON'T BREAK IT. I FIND WHAT WAS ALREADY BROKEN.
**Идея:** Celebrate the tech who touches a simple job and discovers the much worse hidden problem.
**Покупатель:** Avionics technicians / maintainers
**Причина покупки:** Defensive humor + competence pride for the 'black cloud' technician.
**Отличие:** The line is about perception and truth, not systems jargon.
**Визуальное направление:** Storm cloud over a generic aircraft wiring bundle, with hidden fault revealed.
**Смысл для владельца (источник, EN):** The technician investigates one job and uncovers a deeper pre-existing problem. From the outside it can look as though the technician caused the new problem simply because it was discovered while they were working.
**Почему это шутка (источник, EN):** This is defensive technician humor: “I did not break it; I exposed what was already broken.” It celebrates the person who keeps finding hidden faults and then has to explain why the problem is now visible.
**Создано / обновлено:** 2026-09-23 19:58:09.189566+00 / 2026-09-24 22:40:42.70901+00

Компоненты оценки:
- **buyer_desire**: 8.70 (confidence 0.700). purchase_trigger_v2 preliminary score; gate passed; trigger=misunderstood_expertise Дата: 2026-09-23 19:59:53.152527+00.
- **clarity_at_glance**: 9.00 (confidence 0.760). purchase_trigger_v2 preliminary score; gate passed; trigger=misunderstood_expertise Дата: 2026-09-23 19:59:53.152527+00.
- **distinctiveness**: 8.60 (confidence 0.700). purchase_trigger_v2 preliminary score; gate passed; trigger=misunderstood_expertise Дата: 2026-09-23 19:59:53.152527+00.
- **giftability**: 8.50 (confidence 0.670). purchase_trigger_v2 preliminary score; gate passed; trigger=misunderstood_expertise Дата: 2026-09-23 19:59:53.152527+00.
- **insider_resonance**: 9.20 (confidence 0.720). purchase_trigger_v2 preliminary score; gate passed; trigger=misunderstood_expertise Дата: 2026-09-23 19:59:53.152527+00.
- **ip_safety**: 8.90 (confidence 0.600). purchase_trigger_v2 preliminary score; gate passed; trigger=misunderstood_expertise Дата: 2026-09-23 19:59:53.152527+00.
- **niche_fit**: 9.20 (confidence 0.720). purchase_trigger_v2 preliminary score; gate passed; trigger=misunderstood_expertise Дата: 2026-09-23 19:59:53.152527+00.
- **visual_potential**: 8.60 (confidence 0.720). purchase_trigger_v2 preliminary score; gate passed; trigger=misunderstood_expertise Дата: 2026-09-23 19:59:53.152527+00.

#### Avionics — blamed indicator, guilty harness
`v4_av_indicator_innocent` · ID `5b64c6a9-cc6a-4eec-92e6-59954472c000`

**Интерпретация:** Исследовательский кандидат; одобрение владельца не зафиксировано
**Статус БД:** scored · **балл:** 86.62 · **confidence:** 70.32 · **coverage:** 100.00
**Текст / хук:** THE INDICATOR WAS INNOCENT.
**Идея:** A detective story where the obvious suspect is innocent and the hidden wiring is guilty.
**Покупатель:** Avionics technicians / maintainers
**Причина покупки:** Insider detective humor that rewards real troubleshooting over parts swapping.
**Отличие:** The premise is misdiagnosis and discovery, not a wiring vocabulary dump.
**Визуальное направление:** Noir-style suspect board: indicator cleared, harness circled.
**Создано / обновлено:** 2026-09-23 19:58:09.189566+00 / 2026-09-24 05:05:38.621539+00

Компоненты оценки:
- **buyer_desire**: 8.50 (confidence 0.700). purchase_trigger_v2 preliminary score; gate passed; trigger=diagnostic_pride Дата: 2026-09-23 19:59:53.152527+00.
- **clarity_at_glance**: 8.70 (confidence 0.760). purchase_trigger_v2 preliminary score; gate passed; trigger=diagnostic_pride Дата: 2026-09-23 19:59:53.152527+00.
- **distinctiveness**: 8.60 (confidence 0.700). purchase_trigger_v2 preliminary score; gate passed; trigger=diagnostic_pride Дата: 2026-09-23 19:59:53.152527+00.
- **giftability**: 8.10 (confidence 0.670). purchase_trigger_v2 preliminary score; gate passed; trigger=diagnostic_pride Дата: 2026-09-23 19:59:53.152527+00.
- **insider_resonance**: 9.00 (confidence 0.720). purchase_trigger_v2 preliminary score; gate passed; trigger=diagnostic_pride Дата: 2026-09-23 19:59:53.152527+00.
- **ip_safety**: 8.90 (confidence 0.600). purchase_trigger_v2 preliminary score; gate passed; trigger=diagnostic_pride Дата: 2026-09-23 19:59:53.152527+00.
- **niche_fit**: 9.30 (confidence 0.720). purchase_trigger_v2 preliminary score; gate passed; trigger=diagnostic_pride Дата: 2026-09-23 19:59:53.152527+00.
- **visual_potential**: 8.80 (confidence 0.720). purchase_trigger_v2 preliminary score; gate passed; trigger=diagnostic_pride Дата: 2026-09-23 19:59:53.152527+00.

#### Avionics — intermittent until I arrive
`v4_av_intermit_arrival` · ID `5fdc95ea-93ba-49d7-a36d-4ae2bc17505f`

**Интерпретация:** Исследовательский кандидат; одобрение владельца не зафиксировано
**Статус БД:** scored · **балл:** 89.20 · **confidence:** 70.32 · **coverage:** 100.00
**Текст / хук:** INTERMITTENT UNTIL I ARRIVE.
**Идея:** The classic problem that refuses to reproduce for the technician.
**Покупатель:** Avionics technicians / maintainers
**Причина покупки:** Short, wearable, high-recognition troubleshooting humor.
**Отличие:** No jargon density; the joke is the observer effect.
**Визуальное направление:** Fault waveform flattening the moment a technician silhouette appears.
**Создано / обновлено:** 2026-09-23 19:58:09.189566+00 / 2026-09-24 05:05:38.621539+00

Компоненты оценки:
- **buyer_desire**: 8.90 (confidence 0.700). purchase_trigger_v2 preliminary score; gate passed; trigger=intermittent_fault_humor Дата: 2026-09-23 19:59:53.152527+00.
- **clarity_at_glance**: 9.20 (confidence 0.760). purchase_trigger_v2 preliminary score; gate passed; trigger=intermittent_fault_humor Дата: 2026-09-23 19:59:53.152527+00.
- **distinctiveness**: 8.60 (confidence 0.700). purchase_trigger_v2 preliminary score; gate passed; trigger=intermittent_fault_humor Дата: 2026-09-23 19:59:53.152527+00.
- **giftability**: 8.80 (confidence 0.670). purchase_trigger_v2 preliminary score; gate passed; trigger=intermittent_fault_humor Дата: 2026-09-23 19:59:53.152527+00.
- **insider_resonance**: 9.30 (confidence 0.720). purchase_trigger_v2 preliminary score; gate passed; trigger=intermittent_fault_humor Дата: 2026-09-23 19:59:53.152527+00.
- **ip_safety**: 8.90 (confidence 0.600). purchase_trigger_v2 preliminary score; gate passed; trigger=intermittent_fault_humor Дата: 2026-09-23 19:59:53.152527+00.
- **niche_fit**: 9.20 (confidence 0.720). purchase_trigger_v2 preliminary score; gate passed; trigger=intermittent_fault_humor Дата: 2026-09-23 19:59:53.152527+00.
- **visual_potential**: 8.70 (confidence 0.720). purchase_trigger_v2 preliminary score; gate passed; trigger=intermittent_fault_humor Дата: 2026-09-23 19:59:53.152527+00.

#### Avionics — simple squawk, wiring nightmare
`v4_av_simple_squawk` · ID `a95a9e17-bf31-4182-97d2-a50a1f5b6d2f`

**Интерпретация:** Исследовательский кандидат; одобрение владельца не зафиксировано
**Статус БД:** scored · **балл:** 88.64 · **confidence:** 70.32 · **coverage:** 100.00
**Текст / хук:** SIMPLE SQUAWK. EIGHT HOURS OF WIRING.
**Идея:** Turn the gap between a tiny reported symptom and a deep wiring chase into the joke.
**Покупатель:** Avionics technicians / maintainers
**Причина покупки:** Strong insider frustration and diagnostic pride.
**Отличие:** Specific work-story structure; not an acronym list.
**Визуальное направление:** Tiny caution note expanding into an absurd maze of generic wiring.
**Создано / обновлено:** 2026-09-23 19:58:09.189566+00 / 2026-09-24 05:05:38.621539+00

Компоненты оценки:
- **buyer_desire**: 8.80 (confidence 0.700). purchase_trigger_v2 preliminary score; gate passed; trigger=diagnostic_humor Дата: 2026-09-23 19:59:53.152527+00.
- **clarity_at_glance**: 9.10 (confidence 0.760). purchase_trigger_v2 preliminary score; gate passed; trigger=diagnostic_humor Дата: 2026-09-23 19:59:53.152527+00.
- **distinctiveness**: 8.60 (confidence 0.700). purchase_trigger_v2 preliminary score; gate passed; trigger=diagnostic_humor Дата: 2026-09-23 19:59:53.152527+00.
- **giftability**: 8.60 (confidence 0.670). purchase_trigger_v2 preliminary score; gate passed; trigger=diagnostic_humor Дата: 2026-09-23 19:59:53.152527+00.
- **insider_resonance**: 9.20 (confidence 0.720). purchase_trigger_v2 preliminary score; gate passed; trigger=diagnostic_humor Дата: 2026-09-23 19:59:53.152527+00.
- **ip_safety**: 8.90 (confidence 0.600). purchase_trigger_v2 preliminary score; gate passed; trigger=diagnostic_humor Дата: 2026-09-23 19:59:53.152527+00.
- **niche_fit**: 9.30 (confidence 0.720). purchase_trigger_v2 preliminary score; gate passed; trigger=diagnostic_humor Дата: 2026-09-23 19:59:53.152527+00.
- **visual_potential**: 8.80 (confidence 0.720). purchase_trigger_v2 preliminary score; gate passed; trigger=diagnostic_humor Дата: 2026-09-23 19:59:53.152527+00.

#### Avionics — wiring whisperer
`v4_av_wire_whisperer` · ID `06e0a893-7704-44be-83e2-cdb797755177`

**Интерпретация:** V4: понижен редакционным отбором, сохранен в истории
**Статус БД:** scored · **балл:** 84.38 · **confidence:** 70.32 · **coverage:** 100.00
**Текст / хук:** THE WIRES TALK. I JUST LISTEN BETTER.
**Идея:** Playful status concept about electrical troubleshooting being a specialist skill others avoid.
**Покупатель:** Avionics technicians / maintainers
**Причина покупки:** Competence/status without naming a workflow.
**Отличие:** Humanizes the diagnostic relationship rather than listing pins/connectors.
**Визуальное направление:** Abstract waveform flowing through a wire into an ear/headset motif.
**editorial_reason:** generic whisperer formula
**Создано / обновлено:** 2026-09-23 19:58:09.189566+00 / 2026-09-24 05:05:38.621539+00

Компоненты оценки:
- **buyer_desire**: 8.20 (confidence 0.700). purchase_trigger_v2 preliminary score; gate passed; trigger=specialist_pride Дата: 2026-09-23 19:59:53.152527+00.
- **clarity_at_glance**: 8.80 (confidence 0.760). purchase_trigger_v2 preliminary score; gate passed; trigger=specialist_pride Дата: 2026-09-23 19:59:53.152527+00.
- **distinctiveness**: 8.00 (confidence 0.700). purchase_trigger_v2 preliminary score; gate passed; trigger=specialist_pride Дата: 2026-09-23 19:59:53.152527+00.
- **giftability**: 7.90 (confidence 0.670). purchase_trigger_v2 preliminary score; gate passed; trigger=specialist_pride Дата: 2026-09-23 19:59:53.152527+00.
- **insider_resonance**: 8.90 (confidence 0.720). purchase_trigger_v2 preliminary score; gate passed; trigger=specialist_pride Дата: 2026-09-23 19:59:53.152527+00.
- **ip_safety**: 8.90 (confidence 0.600). purchase_trigger_v2 preliminary score; gate passed; trigger=specialist_pride Дата: 2026-09-23 19:59:53.152527+00.
- **niche_fit**: 9.20 (confidence 0.720). purchase_trigger_v2 preliminary score; gate passed; trigger=specialist_pride Дата: 2026-09-23 19:59:53.152527+00.
- **visual_potential**: 8.70 (confidence 0.720). purchase_trigger_v2 preliminary score; gate passed; trigger=specialist_pride Дата: 2026-09-23 19:59:53.152527+00.

## 02. Biomedical Equipment Technician
Ключ: `biomedical_equipment_technician` · ID: `58b924ce-1dbf-4d0e-b959-7ec80b0fb3f5`

**Статус БД:** shortlisted · **балл:** 80.35 · **confidence:** 75.46 · **coverage:** 100.00
**Аудитория:** BMET / clinical engineering technicians
**Категория:** occupational_identity
**Исследовательская аргументация:** Legacy Town Label occupational niche carried forward for re-evaluation under the new niche-first scoring engine. Existing artwork quality does not determine niche status.
**Создано / обновлено:** 2026-09-23 06:11:01.997287+00 / 2026-09-23 10:03:30.159451+00

### Компоненты оценки ниши

- **channel_breadth**: 7.50 (confidence 0.620). Legacy Forge/Town Label niche rescored under the unified Forge rubric using current 2025-35 BLS data plus the 2026-09-21/22 marketplace and IP research already stored in merch.research_notes. Existing visual rejection does not count as niche rejection. Дата: 2026-09-23 09:44:55.053118+00.
- **competition_opportunity**: 7.50 (confidence 0.760). Legacy Forge/Town Label niche rescored under the unified Forge rubric using current 2025-35 BLS data plus the 2026-09-21/22 marketplace and IP research already stored in merch.research_notes. Existing visual rejection does not count as niche rejection. Дата: 2026-09-23 09:44:55.053118+00.
- **concept_depth**: 9.00 (confidence 0.780). Legacy Forge/Town Label niche rescored under the unified Forge rubric using current 2025-35 BLS data plus the 2026-09-21/22 marketplace and IP research already stored in merch.research_notes. Existing visual rejection does not count as niche rejection. Дата: 2026-09-23 09:44:55.053118+00.
- **demand_evidence**: 8.50 (confidence 0.900). Legacy Forge/Town Label niche rescored under the unified Forge rubric using current 2025-35 BLS data plus the 2026-09-21/22 marketplace and IP research already stored in merch.research_notes. Existing visual rejection does not count as niche rejection. Дата: 2026-09-23 09:44:55.053118+00.
- **founder_edge**: 2.00 (confidence 0.400). Legacy Forge/Town Label niche rescored under the unified Forge rubric using current 2025-35 BLS data plus the 2026-09-21/22 marketplace and IP research already stored in merch.research_notes. Existing visual rejection does not count as niche rejection. Дата: 2026-09-23 09:44:55.053118+00.
- **identity_intensity**: 8.00 (confidence 0.720). Legacy Forge/Town Label niche rescored under the unified Forge rubric using current 2025-35 BLS data plus the 2026-09-21/22 marketplace and IP research already stored in merch.research_notes. Existing visual rejection does not count as niche rejection. Дата: 2026-09-23 09:44:55.053118+00.
- **legal_safety**: 7.50 (confidence 0.700). Legacy Forge/Town Label niche rescored under the unified Forge rubric using current 2025-35 BLS data plus the 2026-09-21/22 marketplace and IP research already stored in merch.research_notes. Existing visual rejection does not count as niche rejection. Дата: 2026-09-23 09:44:55.053118+00.
- **purchase_motivation**: 7.80 (confidence 0.680). Legacy Forge/Town Label niche rescored under the unified Forge rubric using current 2025-35 BLS data plus the 2026-09-21/22 marketplace and IP research already stored in merch.research_notes. Existing visual rejection does not count as niche rejection. Дата: 2026-09-23 09:44:55.053118+00.
- **repeatability**: 8.00 (confidence 0.660). Legacy Forge/Town Label niche rescored under the unified Forge rubric using current 2025-35 BLS data plus the 2026-09-21/22 marketplace and IP research already stored in merch.research_notes. Existing visual rejection does not count as niche rejection. Дата: 2026-09-23 09:44:55.053118+00.
- **visual_language**: 9.00 (confidence 0.800). Legacy Forge/Town Label niche rescored under the unified Forge rubric using current 2025-35 BLS data plus the 2026-09-21/22 marketplace and IP research already stored in merch.research_notes. Existing visual rejection does not count as niche rejection. Дата: 2026-09-23 09:44:55.053118+00.

### Концепции (12)

#### BMET — device lifecycle
`bmet_device_lifecycle_pm_repair_return` · ID `cd31de2a-49ce-4453-b267-f1ba519632bd`

**Интерпретация:** Исследовательский кандидат; одобрение владельца не зафиксировано
**Статус БД:** scored · **балл:** 87.15 · **confidence:** 68.17 · **coverage:** 100.00
**Текст / хук:** RECEIVE → PM → REPAIR → RETURN
**Идея:** BMET — device lifecycle. Core hook: RECEIVE → PM → REPAIR → RETURN. Clinical-equipment testing, PM, repair, calibration and documentation. Execution must stay original and descriptive; avoid employer, OEM, certification-body, association and proprietary-interface branding.
**Покупатель:** Biomedical equipment technicians / medical equipment repairers
**Причина покупки:** Identity purchase for biomedical equipment technicians / medical equipment repairers who recognize the real workflow/systems language.
**Отличие:** Insider technical process direction intended to avoid generic profession-title, retro-badge, skull, flag, coffee and parody templates.
**Визуальное направление:** Equipment-service lifecycle from incoming device through preventive maintenance/repair and return to service.
**Создано / обновлено:** 2026-09-23 09:48:50.541446+00 / 2026-09-23 09:55:40.114238+00

Компоненты оценки:
- **buyer_desire**: 8.36 (confidence 0.670). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **clarity_at_glance**: 8.77 (confidence 0.670). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **distinctiveness**: 8.70 (confidence 0.670). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **giftability**: 7.87 (confidence 0.670). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **insider_resonance**: 9.10 (confidence 0.700). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **ip_safety**: 8.80 (confidence 0.670). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **niche_fit**: 9.35 (confidence 0.700). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **visual_potential**: 8.90 (confidence 0.700). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.

#### BMET — electrical safety verification
`bmet_electrical_safety_measure_verify` · ID `109fb498-1762-40b1-b597-31a0dcfa6ab4`

**Интерпретация:** Исследовательский кандидат; одобрение владельца не зафиксировано
**Статус БД:** scored · **балл:** 88.13 · **confidence:** 69.17 · **coverage:** 100.00
**Текст / хук:** MEASURE • VERIFY • RECORD
**Идея:** BMET — electrical safety verification. Core hook: MEASURE • VERIFY • RECORD. Clinical-equipment testing, PM, repair, calibration and documentation. Execution must stay original and descriptive; avoid employer, OEM, certification-body, association and proprietary-interface branding.
**Покупатель:** Biomedical equipment technicians / medical equipment repairers
**Причина покупки:** Identity purchase for biomedical equipment technicians / medical equipment repairers who recognize the real workflow/systems language.
**Отличие:** Insider technical diagnostic direction intended to avoid generic profession-title, retro-badge, skull, flag, coffee and parody templates.
**Визуальное направление:** Electrical-safety-test identity without values, standards logos or manufacturer UI; generic analyzer/test-point visual.
**Создано / обновлено:** 2026-09-23 09:48:50.541446+00 / 2026-09-23 09:55:40.114238+00

Компоненты оценки:
- **buyer_desire**: 8.56 (confidence 0.680). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **clarity_at_glance**: 8.53 (confidence 0.680). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **distinctiveness**: 8.90 (confidence 0.680). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **giftability**: 7.83 (confidence 0.680). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **insider_resonance**: 9.35 (confidence 0.710). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **ip_safety**: 8.70 (confidence 0.680). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **niche_fit**: 9.45 (confidence 0.710). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **visual_potential**: 8.85 (confidence 0.710). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.

#### BMET — PM / inspect / test / document
`bmet_pm_inspect_test_document` · ID `de72c435-efad-4437-89ed-fc95640d8c2d`

**Интерпретация:** Исследовательский кандидат; одобрение владельца не зафиксировано
**Статус БД:** scored · **балл:** 85.66 · **confidence:** 67.17 · **coverage:** 100.00
**Текст / хук:** PM • INSPECT • TEST • DOCUMENT
**Идея:** BMET — PM / inspect / test / document. Core hook: PM • INSPECT • TEST • DOCUMENT. Clinical-equipment testing, PM, repair, calibration and documentation. Execution must stay original and descriptive; avoid employer, OEM, certification-body, association and proprietary-interface branding.
**Покупатель:** Biomedical equipment technicians / medical equipment repairers
**Причина покупки:** Identity purchase for biomedical equipment technicians / medical equipment repairers who recognize the real workflow/systems language.
**Отличие:** Insider technical workflow direction intended to avoid generic profession-title, retro-badge, skull, flag, coffee and parody templates.
**Визуальное направление:** Preventive-maintenance identity using generic clinical-device/test-equipment silhouettes and service-record geometry.
**Создано / обновлено:** 2026-09-23 09:48:50.541446+00 / 2026-09-23 09:55:40.114238+00

Компоненты оценки:
- **buyer_desire**: 8.26 (confidence 0.660). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **clarity_at_glance**: 9.17 (confidence 0.660). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **distinctiveness**: 8.40 (confidence 0.660). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **giftability**: 8.07 (confidence 0.660). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **insider_resonance**: 8.80 (confidence 0.690). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **ip_safety**: 9.00 (confidence 0.660). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **niche_fit**: 9.25 (confidence 0.690). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **visual_potential**: 8.40 (confidence 0.690). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.

#### BMET — sensor to alarm chain
`bmet_sensor_signal_display_alarm` · ID `6aa494a6-f78b-40e5-b69d-4a6f71238d11`

**Интерпретация:** Исследовательский кандидат; одобрение владельца не зафиксировано
**Статус БД:** scored · **балл:** 88.78 · **confidence:** 68.17 · **coverage:** 100.00
**Текст / хук:** SENSOR → SIGNAL → DISPLAY → ALARM
**Идея:** BMET — sensor to alarm chain. Core hook: SENSOR → SIGNAL → DISPLAY → ALARM. Clinical-equipment testing, PM, repair, calibration and documentation. Execution must stay original and descriptive; avoid employer, OEM, certification-body, association and proprietary-interface branding.
**Покупатель:** Biomedical equipment technicians / medical equipment repairers
**Причина покупки:** Identity purchase for biomedical equipment technicians / medical equipment repairers who recognize the real workflow/systems language.
**Отличие:** Insider technical technical map direction intended to avoid generic profession-title, retro-badge, skull, flag, coffee and parody templates.
**Визуальное направление:** Generic clinical signal chain emphasizing technical systems thinking rather than a heartbeat cliché.
**Создано / обновлено:** 2026-09-23 09:48:50.541446+00 / 2026-09-23 10:03:30.159451+00

Компоненты оценки:
- **buyer_desire**: 8.46 (confidence 0.670). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **clarity_at_glance**: 7.80 (confidence 0.670). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **distinctiveness**: 9.30 (confidence 0.670). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **giftability**: 7.50 (confidence 0.670). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **insider_resonance**: 9.35 (confidence 0.700). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **ip_safety**: 8.60 (confidence 0.670). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **niche_fit**: 9.35 (confidence 0.700). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **visual_potential**: 9.65 (confidence 0.700). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.

#### BMET — service call loop
`bmet_service_call_test_fix_verify` · ID `a54bb77e-a4af-47e0-8678-adac5643515c`

**Интерпретация:** Исторический: снят после owner review; не возвращать автоматически
**Статус БД:** scored · **балл:** 89.36 · **confidence:** 69.17 · **coverage:** 100.00
**Текст / хук:** SYMPTOM → TEST → FIX → VERIFY
**Идея:** BMET — service call loop. Core hook: SYMPTOM → TEST → FIX → VERIFY. Clinical-equipment testing, PM, repair, calibration and documentation. Execution must stay original and descriptive; avoid employer, OEM, certification-body, association and proprietary-interface branding.
**Покупатель:** Biomedical equipment technicians / medical equipment repairers
**Причина покупки:** Identity purchase for biomedical equipment technicians / medical equipment repairers who recognize the real workflow/systems language.
**Отличие:** Insider technical diagnostic direction intended to avoid generic profession-title, retro-badge, skull, flag, coffee and parody templates.
**Визуальное направление:** Service-call diagnostic loop with generic equipment, meter and work-order cues.
**retired_reason:** failed purchase-trigger quality bar after owner review
**Создано / обновлено:** 2026-09-23 09:48:50.541446+00 / 2026-09-23 23:40:31.847823+00

Компоненты оценки:
- **buyer_desire**: 8.76 (confidence 0.680). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **clarity_at_glance**: 8.60 (confidence 0.680). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **distinctiveness**: 9.10 (confidence 0.680). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **giftability**: 7.90 (confidence 0.680). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **insider_resonance**: 9.45 (confidence 0.710). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **ip_safety**: 8.70 (confidence 0.680). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **niche_fit**: 9.45 (confidence 0.710). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **visual_potential**: 8.95 (confidence 0.710). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.

#### BMET — test / calibrate / PM / repair
`bmet_test_calibrate_pm_repair` · ID `37ef561c-b0bd-44ab-b08b-61959d5e091c`

**Интерпретация:** Исследовательский кандидат; одобрение владельца не зафиксировано
**Статус БД:** scored · **балл:** 88.05 · **confidence:** 72.41 · **coverage:** 100.00
**Текст / хук:** service-tag / bench-test technical label
**Идея:** Biomedical Equipment Technician technical service graphic using the full descriptive job title plus TEST / CALIBRATE / PM / REPAIR and INSPECT / VERIFY / DOCUMENT. Preferred proof C uses a test-equipment/square-wave visual language, not medical heartbeat imagery. Do not use BIOMED as a standalone headline because an active U.S. BIOMED registration exists for medical electronic equipment.
**Покупатель:** BMET / clinical engineering technicians
**Причина покупки:** under-recognized technical identity inside healthcare; pride in keeping clinical equipment safe and functional
**Отличие:** raw Redbubble count is highly noisy; visible relevant designs skew generic job-title/I-solve-problems/patriotic rather than technical service language
**Создано / обновлено:** 2026-09-23 06:11:42.741293+00 / 2026-09-23 09:51:32.257179+00

Компоненты оценки:
- **buyer_desire**: 8.62 (confidence 0.736). Unified Forge concept-depth score. Profile captures the concept form (technical map, diagnostic, system map, workflow, process or terminology); a small stored concept bias and bounded niche-quality adjustment prevent identical form scores across materially different niches. No visual was generated. Federal/common-law phrase review remains a separate gate. Дата: 2026-09-23 09:51:32.257179+00.
- **clarity_at_glance**: 9.40 (confidence 0.766). Unified Forge concept-depth score. Profile captures the concept form (technical map, diagnostic, system map, workflow, process or terminology); a small stored concept bias and bounded niche-quality adjustment prevent identical form scores across materially different niches. No visual was generated. Federal/common-law phrase review remains a separate gate. Дата: 2026-09-23 09:51:32.257179+00.
- **distinctiveness**: 8.70 (confidence 0.721). Unified Forge concept-depth score. Profile captures the concept form (technical map, diagnostic, system map, workflow, process or terminology); a small stored concept bias and bounded niche-quality adjustment prevent identical form scores across materially different niches. No visual was generated. Federal/common-law phrase review remains a separate gate. Дата: 2026-09-23 09:51:32.257179+00.
- **giftability**: 8.42 (confidence 0.714). Unified Forge concept-depth score. Profile captures the concept form (technical map, diagnostic, system map, workflow, process or terminology); a small stored concept bias and bounded niche-quality adjustment prevent identical form scores across materially different niches. No visual was generated. Federal/common-law phrase review remains a separate gate. Дата: 2026-09-23 09:51:32.257179+00.
- **insider_resonance**: 9.00 (confidence 0.744). Unified Forge concept-depth score. Profile captures the concept form (technical map, diagnostic, system map, workflow, process or terminology); a small stored concept bias and bounded niche-quality adjustment prevent identical form scores across materially different niches. No visual was generated. Federal/common-law phrase review remains a separate gate. Дата: 2026-09-23 09:51:32.257179+00.
- **ip_safety**: 9.10 (confidence 0.550). Unified Forge concept-depth score. Profile captures the concept form (technical map, diagnostic, system map, workflow, process or terminology); a small stored concept bias and bounded niche-quality adjustment prevent identical form scores across materially different niches. No visual was generated. Federal/common-law phrase review remains a separate gate. Дата: 2026-09-23 09:51:32.257179+00.
- **niche_fit**: 9.32 (confidence 0.751). Unified Forge concept-depth score. Profile captures the concept form (technical map, diagnostic, system map, workflow, process or terminology); a small stored concept bias and bounded niche-quality adjustment prevent identical form scores across materially different niches. No visual was generated. Federal/common-law phrase review remains a separate gate. Дата: 2026-09-23 09:51:32.257179+00.
- **visual_potential**: 8.50 (confidence 0.714). Unified Forge concept-depth score. Profile captures the concept form (technical map, diagnostic, system map, workflow, process or terminology); a small stored concept bias and bounded niche-quality adjustment prevent identical form scores across materially different niches. No visual was generated. Federal/common-law phrase review remains a separate gate. Дата: 2026-09-23 09:51:32.257179+00.

#### BMET — test bench
`bmet_test_equipment_bench` · ID `0ce6978b-1347-4244-a33f-e4615c941d47`

**Интерпретация:** Исследовательский кандидат; одобрение владельца не зафиксировано
**Статус БД:** scored · **балл:** 88.17 · **confidence:** 69.17 · **coverage:** 100.00
**Текст / хук:** DEVICE • ANALYZER • METER • RESULT
**Идея:** BMET — test bench. Core hook: DEVICE • ANALYZER • METER • RESULT. Clinical-equipment testing, PM, repair, calibration and documentation. Execution must stay original and descriptive; avoid employer, OEM, certification-body, association and proprietary-interface branding.
**Покупатель:** Biomedical equipment technicians / medical equipment repairers
**Причина покупки:** Identity purchase for biomedical equipment technicians / medical equipment repairers who recognize the real workflow/systems language.
**Отличие:** Insider technical system map direction intended to avoid generic profession-title, retro-badge, skull, flag, coffee and parody templates.
**Визуальное направление:** Bench-service composition with original generic patient-care device and test equipment; no proprietary product shape emphasis.
**Создано / обновлено:** 2026-09-23 09:48:50.541446+00 / 2026-09-23 09:55:40.114238+00

Компоненты оценки:
- **buyer_desire**: 8.46 (confidence 0.680). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **clarity_at_glance**: 8.17 (confidence 0.680). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **distinctiveness**: 9.00 (confidence 0.680). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **giftability**: 7.57 (confidence 0.680). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **insider_resonance**: 9.10 (confidence 0.710). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **ip_safety**: 8.80 (confidence 0.680). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **niche_fit**: 9.35 (confidence 0.710). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **visual_potential**: 9.60 (confidence 0.710). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.

#### BMET — the dramatic broken call
`v4_bmet_broken_call_plug` · ID `0efe30c1-d003-45d0-bb4d-c32c2be8cce2`

**Интерпретация:** Исследовательский кандидат; одобрение владельца не зафиксировано
**Статус БД:** scored · **балл:** 88.35 · **confidence:** 70.32 · **coverage:** 100.00
**Текст / хук:** THE CALL SAID BROKEN. THE PLUG DISAGREED.
**Идея:** A hospital calls Biomed for a scary broken-device problem; the punchline is a painfully simple user-side cause.
**Покупатель:** BMET / clinical engineering technicians
**Причина покупки:** Humor and solidarity around absurdly simple fixes arriving as urgent equipment failures.
**Отличие:** Not a list of devices or tasks; the joke is the mismatch between drama and diagnosis.
**Визуальное направление:** Minimal alert-screen composition leading to a tiny unplugged-cord reveal; no branded equipment.
**Создано / обновлено:** 2026-09-23 19:58:09.189566+00 / 2026-09-24 05:05:38.621539+00

Компоненты оценки:
- **buyer_desire**: 8.80 (confidence 0.700). purchase_trigger_v2 preliminary score; gate passed; trigger=frustration_humor Дата: 2026-09-23 19:59:53.152527+00.
- **clarity_at_glance**: 9.10 (confidence 0.760). purchase_trigger_v2 preliminary score; gate passed; trigger=frustration_humor Дата: 2026-09-23 19:59:53.152527+00.
- **distinctiveness**: 8.50 (confidence 0.700). purchase_trigger_v2 preliminary score; gate passed; trigger=frustration_humor Дата: 2026-09-23 19:59:53.152527+00.
- **giftability**: 8.70 (confidence 0.670). purchase_trigger_v2 preliminary score; gate passed; trigger=frustration_humor Дата: 2026-09-23 19:59:53.152527+00.
- **insider_resonance**: 9.20 (confidence 0.720). purchase_trigger_v2 preliminary score; gate passed; trigger=frustration_humor Дата: 2026-09-23 19:59:53.152527+00.
- **ip_safety**: 8.90 (confidence 0.600). purchase_trigger_v2 preliminary score; gate passed; trigger=frustration_humor Дата: 2026-09-23 19:59:53.152527+00.
- **niche_fit**: 9.30 (confidence 0.720). purchase_trigger_v2 preliminary score; gate passed; trigger=frustration_humor Дата: 2026-09-23 19:59:53.152527+00.
- **visual_potential**: 8.60 (confidence 0.720). purchase_trigger_v2 preliminary score; gate passed; trigger=frustration_humor Дата: 2026-09-23 19:59:53.152527+00.

#### BMET — calm in the panic
`v4_bmet_calm_room` · ID `cbecfc72-7379-4633-9c16-4a7f29138fba`

**Интерпретация:** Исследовательский кандидат; одобрение владельца не зафиксировано
**Статус БД:** scored · **балл:** 84.49 · **confidence:** 70.32 · **coverage:** 100.00
**Текст / хук:** EVERYONE PANIC. I'LL CHECK THE SIMPLE STUFF.
**Идея:** Identity concept about being the technical calm person in a room where everyone thinks the equipment is failing.
**Покупатель:** BMET / clinical engineering technicians
**Причина покупки:** Status + humor: the wearer signals calm diagnostic competence.
**Отличие:** No jargon required; BMET specificity comes from the clinical-equipment context.
**Визуальное направление:** Calm technician silhouette against chaotic alert icons; no hospital branding.
**Создано / обновлено:** 2026-09-23 19:58:09.189566+00 / 2026-09-24 05:05:38.621539+00

Компоненты оценки:
- **buyer_desire**: 8.30 (confidence 0.700). purchase_trigger_v2 preliminary score; gate passed; trigger=competence_pride Дата: 2026-09-23 19:59:53.152527+00.
- **clarity_at_glance**: 8.80 (confidence 0.760). purchase_trigger_v2 preliminary score; gate passed; trigger=competence_pride Дата: 2026-09-23 19:59:53.152527+00.
- **distinctiveness**: 8.20 (confidence 0.700). purchase_trigger_v2 preliminary score; gate passed; trigger=competence_pride Дата: 2026-09-23 19:59:53.152527+00.
- **giftability**: 8.00 (confidence 0.670). purchase_trigger_v2 preliminary score; gate passed; trigger=competence_pride Дата: 2026-09-23 19:59:53.152527+00.
- **insider_resonance**: 8.70 (confidence 0.720). purchase_trigger_v2 preliminary score; gate passed; trigger=competence_pride Дата: 2026-09-23 19:59:53.152527+00.
- **ip_safety**: 8.90 (confidence 0.600). purchase_trigger_v2 preliminary score; gate passed; trigger=competence_pride Дата: 2026-09-23 19:59:53.152527+00.
- **niche_fit**: 9.10 (confidence 0.720). purchase_trigger_v2 preliminary score; gate passed; trigger=competence_pride Дата: 2026-09-23 19:59:53.152527+00.
- **visual_potential**: 8.50 (confidence 0.720). purchase_trigger_v2 preliminary score; gate passed; trigger=competence_pride Дата: 2026-09-23 19:59:53.152527+00.

#### BMET — equipment hide-and-seek
`v4_bmet_hide_seek` · ID `218c558d-315f-4179-a0e8-a005f841a586`

**Интерпретация:** Исследовательский кандидат; одобрение владельца не зафиксировано
**Статус БД:** scored · **балл:** 87.85 · **confidence:** 70.32 · **coverage:** 100.00
**Текст / хук:** HOSPITAL HIDE-AND-SEEK: EQUIPMENT EDITION
**Идея:** Turn the daily hunt for supposedly missing equipment into a detective / hide-and-seek identity joke.
**Покупатель:** BMET / clinical engineering technicians
**Причина покупки:** Shared frustration becomes a playful identity badge and giftable inside joke.
**Отличие:** Specific to BMET life through the situation, not by stacking technical terms.
**Визуальное направление:** Detective-board / floor-map visual with generic equipment silhouettes hiding in absurd places.
**Создано / обновлено:** 2026-09-23 19:58:09.189566+00 / 2026-09-24 05:05:38.621539+00

Компоненты оценки:
- **buyer_desire**: 8.70 (confidence 0.700). purchase_trigger_v2 preliminary score; gate passed; trigger=shared_frustration Дата: 2026-09-23 19:59:53.152527+00.
- **clarity_at_glance**: 9.00 (confidence 0.760). purchase_trigger_v2 preliminary score; gate passed; trigger=shared_frustration Дата: 2026-09-23 19:59:53.152527+00.
- **distinctiveness**: 8.50 (confidence 0.700). purchase_trigger_v2 preliminary score; gate passed; trigger=shared_frustration Дата: 2026-09-23 19:59:53.152527+00.
- **giftability**: 8.70 (confidence 0.670). purchase_trigger_v2 preliminary score; gate passed; trigger=shared_frustration Дата: 2026-09-23 19:59:53.152527+00.
- **insider_resonance**: 9.20 (confidence 0.720). purchase_trigger_v2 preliminary score; gate passed; trigger=shared_frustration Дата: 2026-09-23 19:59:53.152527+00.
- **ip_safety**: 8.90 (confidence 0.600). purchase_trigger_v2 preliminary score; gate passed; trigger=shared_frustration Дата: 2026-09-23 19:59:53.152527+00.
- **niche_fit**: 9.30 (confidence 0.720). purchase_trigger_v2 preliminary score; gate passed; trigger=shared_frustration Дата: 2026-09-23 19:59:53.152527+00.
- **visual_potential**: 8.50 (confidence 0.720). purchase_trigger_v2 preliminary score; gate passed; trigger=shared_frustration Дата: 2026-09-23 19:59:53.152527+00.

#### BMET — batteries after midnight
`v4_bmet_on_call_battery` · ID `f989161d-1d59-4902-8c44-55ddd74dd81d`

**Интерпретация:** Исследовательский кандидат; одобрение владельца не зафиксировано
**Статус БД:** scored · **балл:** 86.65 · **confidence:** 70.32 · **coverage:** 100.00
**Текст / хук:** BATTERIES RESPECT NO BEDTIME.
**Идея:** On-call humor about mundane failures choosing the least convenient hour.
**Покупатель:** BMET / clinical engineering technicians
**Причина покупки:** Giftable on-call gallows humor without attacking patients or clinicians.
**Отличие:** The joke is timing and fatigue, not a battery checklist.
**Визуальное направление:** Moon / pager / low-battery visual, generic and non-branded.
**Создано / обновлено:** 2026-09-23 19:58:09.189566+00 / 2026-09-24 05:05:38.621539+00

Компоненты оценки:
- **buyer_desire**: 8.60 (confidence 0.700). purchase_trigger_v2 preliminary score; gate passed; trigger=on_call_humor Дата: 2026-09-23 19:59:53.152527+00.
- **clarity_at_glance**: 9.00 (confidence 0.760). purchase_trigger_v2 preliminary score; gate passed; trigger=on_call_humor Дата: 2026-09-23 19:59:53.152527+00.
- **distinctiveness**: 8.20 (confidence 0.700). purchase_trigger_v2 preliminary score; gate passed; trigger=on_call_humor Дата: 2026-09-23 19:59:53.152527+00.
- **giftability**: 8.80 (confidence 0.670). purchase_trigger_v2 preliminary score; gate passed; trigger=on_call_humor Дата: 2026-09-23 19:59:53.152527+00.
- **insider_resonance**: 8.90 (confidence 0.720). purchase_trigger_v2 preliminary score; gate passed; trigger=on_call_humor Дата: 2026-09-23 19:59:53.152527+00.
- **ip_safety**: 8.90 (confidence 0.600). purchase_trigger_v2 preliminary score; gate passed; trigger=on_call_humor Дата: 2026-09-23 19:59:53.152527+00.
- **niche_fit**: 9.10 (confidence 0.720). purchase_trigger_v2 preliminary score; gate passed; trigger=on_call_humor Дата: 2026-09-23 19:59:53.152527+00.
- **visual_potential**: 8.50 (confidence 0.720). purchase_trigger_v2 preliminary score; gate passed; trigger=on_call_humor Дата: 2026-09-23 19:59:53.152527+00.

#### BMET — twenty-minute walk, thirty-second fix
`v4_bmet_walk_vs_fix` · ID `a67960a1-9f77-4712-96ee-9b517e5bf7d4`

**Интерпретация:** V4: редакционный финалист на выбор владельца, НЕ подтвержденное одобрение
**Статус БД:** shortlisted · **балл:** 89.79 · **confidence:** 70.32 · **coverage:** 100.00
**Текст / хук:** 20-MINUTE WALK. 30-SECOND FIX.
**Идея:** Celebrate the disproportion between the time spent getting to a call and the tiny fix itself.
**Покупатель:** BMET / clinical engineering technicians
**Причина покупки:** A concise work-story joke that a BMET can wear and another BMET can instantly validate.
**Отличие:** The value is the absurd ratio, not terminology.
**Визуальное направление:** Large 20:00 versus 0:30 typography with a small generic tool icon.
**Смысл для владельца (источник, EN):** The technician may spend much longer walking across a large hospital to reach a service call than the actual repair takes once they arrive.
**Почему это шутка (источник, EN):** The insider recognition is the ratio: a long trip through the building for a tiny fix. It is funny because the logistics can be more time-consuming than the technical problem.
**Создано / обновлено:** 2026-09-23 19:58:09.189566+00 / 2026-09-24 22:40:42.70901+00

Компоненты оценки:
- **buyer_desire**: 9.10 (confidence 0.700). purchase_trigger_v2 preliminary score; gate passed; trigger=work_absurdity Дата: 2026-09-23 19:59:53.152527+00.
- **clarity_at_glance**: 9.30 (confidence 0.760). purchase_trigger_v2 preliminary score; gate passed; trigger=work_absurdity Дата: 2026-09-23 19:59:53.152527+00.
- **distinctiveness**: 8.70 (confidence 0.700). purchase_trigger_v2 preliminary score; gate passed; trigger=work_absurdity Дата: 2026-09-23 19:59:53.152527+00.
- **giftability**: 8.80 (confidence 0.670). purchase_trigger_v2 preliminary score; gate passed; trigger=work_absurdity Дата: 2026-09-23 19:59:53.152527+00.
- **insider_resonance**: 9.30 (confidence 0.720). purchase_trigger_v2 preliminary score; gate passed; trigger=work_absurdity Дата: 2026-09-23 19:59:53.152527+00.
- **ip_safety**: 8.90 (confidence 0.600). purchase_trigger_v2 preliminary score; gate passed; trigger=work_absurdity Дата: 2026-09-23 19:59:53.152527+00.
- **niche_fit**: 9.20 (confidence 0.720). purchase_trigger_v2 preliminary score; gate passed; trigger=work_absurdity Дата: 2026-09-23 19:59:53.152527+00.
- **visual_potential**: 8.50 (confidence 0.720). purchase_trigger_v2 preliminary score; gate passed; trigger=work_absurdity Дата: 2026-09-23 19:59:53.152527+00.

## 03. Calibration Technician
Ключ: `calibration_technician` · ID: `3641e68f-a764-482e-b5e8-7e42366a6a15`

**Статус БД:** scored · **балл:** 78.75 · **confidence:** 76.38 · **coverage:** 100.00
**Аудитория:** Calibration / metrology technicians
**Категория:** occupational_identity
**Исследовательская аргументация:** Legacy Town Label occupational niche carried forward for re-evaluation under the new niche-first scoring engine. Existing artwork quality does not determine niche status.
**Создано / обновлено:** 2026-09-23 06:11:01.997287+00 / 2026-09-23 10:03:30.159451+00

### Компоненты оценки ниши

- **channel_breadth**: 7.00 (confidence 0.600). Legacy Forge/Town Label niche rescored under the unified Forge rubric using current 2025-35 BLS data plus the 2026-09-21/22 marketplace and IP research already stored in merch.research_notes. Existing visual rejection does not count as niche rejection. Дата: 2026-09-23 09:44:55.053118+00.
- **competition_opportunity**: 8.50 (confidence 0.760). Legacy Forge/Town Label niche rescored under the unified Forge rubric using current 2025-35 BLS data plus the 2026-09-21/22 marketplace and IP research already stored in merch.research_notes. Existing visual rejection does not count as niche rejection. Дата: 2026-09-23 09:44:55.053118+00.
- **concept_depth**: 9.50 (confidence 0.820). Legacy Forge/Town Label niche rescored under the unified Forge rubric using current 2025-35 BLS data plus the 2026-09-21/22 marketplace and IP research already stored in merch.research_notes. Existing visual rejection does not count as niche rejection. Дата: 2026-09-23 09:44:55.053118+00.
- **demand_evidence**: 6.50 (confidence 0.900). Legacy Forge/Town Label niche rescored under the unified Forge rubric using current 2025-35 BLS data plus the 2026-09-21/22 marketplace and IP research already stored in merch.research_notes. Existing visual rejection does not count as niche rejection. Дата: 2026-09-23 09:44:55.053118+00.
- **founder_edge**: 2.00 (confidence 0.400). Legacy Forge/Town Label niche rescored under the unified Forge rubric using current 2025-35 BLS data plus the 2026-09-21/22 marketplace and IP research already stored in merch.research_notes. Existing visual rejection does not count as niche rejection. Дата: 2026-09-23 09:44:55.053118+00.
- **identity_intensity**: 8.50 (confidence 0.740). Legacy Forge/Town Label niche rescored under the unified Forge rubric using current 2025-35 BLS data plus the 2026-09-21/22 marketplace and IP research already stored in merch.research_notes. Existing visual rejection does not count as niche rejection. Дата: 2026-09-23 09:44:55.053118+00.
- **legal_safety**: 7.00 (confidence 0.740). Legacy Forge/Town Label niche rescored under the unified Forge rubric using current 2025-35 BLS data plus the 2026-09-21/22 marketplace and IP research already stored in merch.research_notes. Existing visual rejection does not count as niche rejection. Дата: 2026-09-23 09:44:55.053118+00.
- **purchase_motivation**: 7.50 (confidence 0.660). Legacy Forge/Town Label niche rescored under the unified Forge rubric using current 2025-35 BLS data plus the 2026-09-21/22 marketplace and IP research already stored in merch.research_notes. Existing visual rejection does not count as niche rejection. Дата: 2026-09-23 09:44:55.053118+00.
- **repeatability**: 8.00 (confidence 0.680). Legacy Forge/Town Label niche rescored under the unified Forge rubric using current 2025-35 BLS data plus the 2026-09-21/22 marketplace and IP research already stored in merch.research_notes. Existing visual rejection does not count as niche rejection. Дата: 2026-09-23 09:44:55.053118+00.
- **visual_language**: 9.50 (confidence 0.840). Legacy Forge/Town Label niche rescored under the unified Forge rubric using current 2025-35 BLS data plus the 2026-09-21/22 marketplace and IP research already stored in merch.research_notes. Existing visual rejection does not count as niche rejection. Дата: 2026-09-23 09:44:55.053118+00.

### Концепции (7)

#### Calibration — as-found / as-left
`cal_as_found_as_left` · ID `d002e78a-ecd8-4b4e-a267-bb6909328c9a`

**Интерпретация:** Исследовательский кандидат; одобрение владельца не зафиксировано
**Статус БД:** scored · **балл:** 86.89 · **confidence:** 67.17 · **coverage:** 100.00
**Текст / хук:** AS-FOUND • AS-LEFT
**Идея:** Calibration — as-found / as-left. Core hook: AS-FOUND • AS-LEFT. Measurement comparison, standards, uncertainty, calibration records and verification. Execution must stay original and descriptive; avoid employer, OEM, certification-body, association and proprietary-interface branding.
**Покупатель:** Calibration / metrology technicians
**Причина покупки:** Identity purchase for calibration / metrology technicians who recognize the real workflow/systems language.
**Отличие:** Insider technical terminology direction intended to avoid generic profession-title, retro-badge, skull, flag, coffee and parody templates.
**Визуальное направление:** Two-state calibration record concept with before/after measurement traces; no branded forms.
**Создано / обновлено:** 2026-09-23 09:48:50.541446+00 / 2026-09-23 09:55:40.114238+00

Компоненты оценки:
- **buyer_desire**: 8.02 (confidence 0.660). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **clarity_at_glance**: 9.27 (confidence 0.660). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **distinctiveness**: 8.50 (confidence 0.660). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **giftability**: 8.17 (confidence 0.660). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **insider_resonance**: 9.50 (confidence 0.690). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **ip_safety**: 8.80 (confidence 0.660). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **niche_fit**: 9.42 (confidence 0.690). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **visual_potential**: 8.50 (confidence 0.690). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.

#### Calibration — compare / verify / record
`cal_compare_verify_record` · ID `349a632a-2a86-4d35-8cfc-03fc101a1745`

**Интерпретация:** Исследовательский кандидат; одобрение владельца не зафиксировано
**Статус БД:** scored · **балл:** 85.55 · **confidence:** 67.17 · **coverage:** 100.00
**Текст / хук:** COMPARE • VERIFY • RECORD
**Идея:** Calibration — compare / verify / record. Core hook: COMPARE • VERIFY • RECORD. Measurement comparison, standards, uncertainty, calibration records and verification. Execution must stay original and descriptive; avoid employer, OEM, certification-body, association and proprietary-interface branding.
**Покупатель:** Calibration / metrology technicians
**Причина покупки:** Identity purchase for calibration / metrology technicians who recognize the real workflow/systems language.
**Отличие:** Insider technical workflow direction intended to avoid generic profession-title, retro-badge, skull, flag, coffee and parody templates.
**Визуальное направление:** Calibration workflow explicitly avoiding the claim that adjustment is always part of calibration.
**Создано / обновлено:** 2026-09-23 09:48:50.541446+00 / 2026-09-23 09:55:40.114238+00

Компоненты оценки:
- **buyer_desire**: 8.22 (confidence 0.660). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **clarity_at_glance**: 9.17 (confidence 0.660). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **distinctiveness**: 8.40 (confidence 0.660). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **giftability**: 8.07 (confidence 0.660). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **insider_resonance**: 8.80 (confidence 0.690). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **ip_safety**: 9.00 (confidence 0.660). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **niche_fit**: 9.22 (confidence 0.690). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **visual_potential**: 8.40 (confidence 0.690). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.

#### Calibration — measurement chain
`cal_measurement_chain_reference_standard_uut` · ID `4cf7c589-f2b3-414b-950b-fab8ea481f53`

**Интерпретация:** Исследовательский кандидат; одобрение владельца не зафиксировано
**Статус БД:** scored · **балл:** 88.06 · **confidence:** 68.17 · **coverage:** 100.00
**Текст / хук:** STANDARD → REFERENCE → UUT
**Идея:** Calibration — measurement chain. Core hook: STANDARD → REFERENCE → UUT. Measurement comparison, standards, uncertainty, calibration records and verification. Execution must stay original and descriptive; avoid employer, OEM, certification-body, association and proprietary-interface branding.
**Покупатель:** Calibration / metrology technicians
**Причина покупки:** Identity purchase for calibration / metrology technicians who recognize the real workflow/systems language.
**Отличие:** Insider technical technical map direction intended to avoid generic profession-title, retro-badge, skull, flag, coffee and parody templates.
**Визуальное направление:** Generic measurement-chain hierarchy; avoids using TRACEABLE as a brand-like headline.
**Создано / обновлено:** 2026-09-23 09:48:50.541446+00 / 2026-09-23 09:55:40.114238+00

Компоненты оценки:
- **buyer_desire**: 8.32 (confidence 0.670). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **clarity_at_glance**: 7.77 (confidence 0.670). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **distinctiveness**: 9.20 (confidence 0.670). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **giftability**: 7.47 (confidence 0.670). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **insider_resonance**: 9.30 (confidence 0.700). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **ip_safety**: 8.60 (confidence 0.670). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **niche_fit**: 9.32 (confidence 0.700). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **visual_potential**: 9.60 (confidence 0.700). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.

#### Calibration — reference / UUT / result
`cal_reference_uut_result` · ID `4c8d71c3-cd61-4bef-85a4-fdb0d978b91f`

**Интерпретация:** Исследовательский кандидат; одобрение владельца не зафиксировано
**Статус БД:** scored · **балл:** 88.67 · **confidence:** 69.17 · **coverage:** 100.00
**Текст / хук:** REFERENCE → UUT → RESULT
**Идея:** Calibration — reference / UUT / result. Core hook: REFERENCE → UUT → RESULT. Measurement comparison, standards, uncertainty, calibration records and verification. Execution must stay original and descriptive; avoid employer, OEM, certification-body, association and proprietary-interface branding.
**Покупатель:** Calibration / metrology technicians
**Причина покупки:** Identity purchase for calibration / metrology technicians who recognize the real workflow/systems language.
**Отличие:** Insider technical system map direction intended to avoid generic profession-title, retro-badge, skull, flag, coffee and parody templates.
**Визуальное направление:** Measurement-comparison chain with generic standard, unit-under-test and result block.
**Создано / обновлено:** 2026-09-23 09:48:50.541446+00 / 2026-09-23 09:57:07.855981+00

Компоненты оценки:
- **buyer_desire**: 8.52 (confidence 0.680). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **clarity_at_glance**: 8.20 (confidence 0.680). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **distinctiveness**: 9.10 (confidence 0.680). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **giftability**: 7.60 (confidence 0.680). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **insider_resonance**: 9.15 (confidence 0.710). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **ip_safety**: 8.80 (confidence 0.680). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **niche_fit**: 9.32 (confidence 0.710). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **visual_potential**: 9.65 (confidence 0.710). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.

#### Calibration — measurement quality
`cal_uncertainty_tolerance_repeatability` · ID `f0f4d69d-3241-482e-84a7-868a8d7a176f`

**Интерпретация:** Исследовательский кандидат; одобрение владельца не зафиксировано
**Статус БД:** scored · **балл:** 88.67 · **confidence:** 68.17 · **coverage:** 100.00
**Текст / хук:** UNCERTAINTY • TOLERANCE • REPEATABILITY
**Идея:** Calibration — measurement quality. Core hook: UNCERTAINTY • TOLERANCE • REPEATABILITY. Measurement comparison, standards, uncertainty, calibration records and verification. Execution must stay original and descriptive; avoid employer, OEM, certification-body, association and proprietary-interface branding.
**Покупатель:** Calibration / metrology technicians
**Причина покупки:** Identity purchase for calibration / metrology technicians who recognize the real workflow/systems language.
**Отличие:** Insider technical technical map direction intended to avoid generic profession-title, retro-badge, skull, flag, coffee and parody templates.
**Визуальное направление:** Metrology vocabulary with original uncertainty-band, tolerance-zone and repeatability marks.
**Создано / обновлено:** 2026-09-23 09:48:50.541446+00 / 2026-09-23 09:55:40.114238+00

Компоненты оценки:
- **buyer_desire**: 8.42 (confidence 0.670). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **clarity_at_glance**: 7.80 (confidence 0.670). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **distinctiveness**: 9.30 (confidence 0.670). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **giftability**: 7.50 (confidence 0.670). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **insider_resonance**: 9.35 (confidence 0.700). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **ip_safety**: 8.60 (confidence 0.670). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **niche_fit**: 9.32 (confidence 0.700). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **visual_potential**: 9.65 (confidence 0.700). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.

#### Calibration — zero / span / linearity
`cal_zero_span_linearity` · ID `8e09e9f9-ce5c-4fec-a405-45b5e88d892c`

**Интерпретация:** Исследовательский кандидат; одобрение владельца не зафиксировано
**Статус БД:** scored · **балл:** 86.89 · **confidence:** 67.17 · **coverage:** 100.00
**Текст / хук:** ZERO • SPAN • LINEARITY
**Идея:** Calibration — zero / span / linearity. Core hook: ZERO • SPAN • LINEARITY. Measurement comparison, standards, uncertainty, calibration records and verification. Execution must stay original and descriptive; avoid employer, OEM, certification-body, association and proprietary-interface branding.
**Покупатель:** Calibration / metrology technicians
**Причина покупки:** Identity purchase for calibration / metrology technicians who recognize the real workflow/systems language.
**Отличие:** Insider technical terminology direction intended to avoid generic profession-title, retro-badge, skull, flag, coffee and parody templates.
**Визуальное направление:** Three measurement characteristics rendered as original scale/response graphics.
**Создано / обновлено:** 2026-09-23 09:48:50.541446+00 / 2026-09-23 09:55:40.114238+00

Компоненты оценки:
- **buyer_desire**: 8.02 (confidence 0.660). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **clarity_at_glance**: 9.27 (confidence 0.660). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **distinctiveness**: 8.50 (confidence 0.660). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **giftability**: 8.17 (confidence 0.660). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **insider_resonance**: 9.50 (confidence 0.690). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **ip_safety**: 8.80 (confidence 0.660). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **niche_fit**: 9.42 (confidence 0.690). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **visual_potential**: 8.50 (confidence 0.690). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.

#### Calibration — measurement control
`calibration_measurement_control` · ID `022f55fd-3465-48e8-824e-c65927794c32`

**Интерпретация:** Исследовательский кандидат; одобрение владельца не зафиксировано
**Статус БД:** scored · **балл:** 89.23 · **confidence:** 73.25 · **coverage:** 100.00
**Текст / хук:** REFERENCE → UUT → RESULT | MEASURE • COMPARE • VERIFY • RECORD
**Идея:** Calibration Technician professional metrology graphic. Preferred research proof C: CALIBRATION TECHNICIAN / MEASUREMENT CONTROL with REFERENCE — UUT — RESULT, MEASURE • COMPARE • VERIFY • RECORD, and UNCERTAINTY • TOLERANCE • REPEATABILITY. Do not use TRACEABLE as a headline because Traceable® is an active measurement-instrument brand; do not imply that calibration itself necessarily includes adjustment, because adjustment/repair are separate actions that may follow calibration.
**Покупатель:** Calibration / metrology technicians
**Причина покупки:** small but technically distinctive profession with strong insider vocabulary and weak visible merch sophistication
**Отличие:** Current directly relevant visible merch is sparse and dominated by generic job-title, coffee/cute/important, I-solve-problems and close-enough humor.
**Создано / обновлено:** 2026-09-23 06:11:42.741293+00 / 2026-09-23 10:17:05.900325+00

Компоненты оценки:
- **buyer_desire**: 8.34 (confidence 0.731). Unified Forge concept-depth score. Profile captures the concept form (technical map, diagnostic, system map, workflow, process or terminology); a small stored concept bias and bounded niche-quality adjustment prevent identical form scores across materially different niches. No visual was generated. Federal/common-law phrase review remains a separate gate. Дата: 2026-09-23 09:51:32.257179+00.
- **clarity_at_glance**: 7.90 (confidence 0.701). Unified Forge concept-depth score. Profile captures the concept form (technical map, diagnostic, system map, workflow, process or terminology); a small stored concept bias and bounded niche-quality adjustment prevent identical form scores across materially different niches. No visual was generated. Federal/common-law phrase review remains a separate gate. Дата: 2026-09-23 09:51:32.257179+00.
- **distinctiveness**: 9.40 (confidence 0.746). Unified Forge concept-depth score. Profile captures the concept form (technical map, diagnostic, system map, workflow, process or terminology); a small stored concept bias and bounded niche-quality adjustment prevent identical form scores across materially different niches. No visual was generated. Federal/common-law phrase review remains a separate gate. Дата: 2026-09-23 09:51:32.257179+00.
- **giftability**: 7.34 (confidence 0.686). Unified Forge concept-depth score. Profile captures the concept form (technical map, diagnostic, system map, workflow, process or terminology); a small stored concept bias and bounded niche-quality adjustment prevent identical form scores across materially different niches. No visual was generated. Federal/common-law phrase review remains a separate gate. Дата: 2026-09-23 09:51:32.257179+00.
- **insider_resonance**: 9.40 (confidence 0.761). Unified Forge concept-depth score. Profile captures the concept form (technical map, diagnostic, system map, workflow, process or terminology); a small stored concept bias and bounded niche-quality adjustment prevent identical form scores across materially different niches. No visual was generated. Federal/common-law phrase review remains a separate gate. Дата: 2026-09-23 09:51:32.257179+00.
- **ip_safety**: 8.90 (confidence 0.550). Unified Forge concept-depth score. Profile captures the concept form (technical map, diagnostic, system map, workflow, process or terminology); a small stored concept bias and bounded niche-quality adjustment prevent identical form scores across materially different niches. No visual was generated. Federal/common-law phrase review remains a separate gate. Дата: 2026-09-23 09:51:32.257179+00.
- **niche_fit**: 9.54 (confidence 0.761). Unified Forge concept-depth score. Profile captures the concept form (technical map, diagnostic, system map, workflow, process or terminology); a small stored concept bias and bounded niche-quality adjustment prevent identical form scores across materially different niches. No visual was generated. Federal/common-law phrase review remains a separate gate. Дата: 2026-09-23 09:51:32.257179+00.
- **visual_potential**: 9.80 (confidence 0.776). Unified Forge concept-depth score. Profile captures the concept form (technical map, diagnostic, system map, workflow, process or terminology); a small stored concept bias and bounded niche-quality adjustment prevent identical form scores across materially different niches. No visual was generated. Federal/common-law phrase review remains a separate gate. Дата: 2026-09-23 09:51:32.257179+00.

## 04. Cardiovascular Perfusionist
Ключ: `cardiovascular_perfusionist` · ID: `8cc6069b-5866-49de-a8a4-35ddfc2d9c62`

**Статус БД:** scored · **балл:** 75.90 · **confidence:** 67.26 · **coverage:** 100.00
**Аудитория:** Clinical perfusionists operating heart-lung and extracorporeal circulation systems
**Категория:** occupational_identity
**Исследовательская аргументация:** Highly specialized cardiac-surgery profession with exceptional heart-lung circuit and flow/pressure visual language. Exact national employment sizing is not clean in current O*NET/BLS surfacing; current Etsy market is meaningful at roughly 47–55 relevant items.
**Создано / обновлено:** 2026-09-23 10:00:20.805089+00 / 2026-09-23 10:04:52.652496+00

### Компоненты оценки ниши

- **channel_breadth**: 7.00 (confidence 0.540). Forge pool-completion provisional score using current BLS/O*NET evidence and sampled Etsy competition. Lower confidence is intentional where exact employment sizing or clean marketplace decomposition is unavailable. Дата: 2026-09-23 10:04:52.652496+00.
- **competition_opportunity**: 6.50 (confidence 0.780). Forge pool-completion provisional score using current BLS/O*NET evidence and sampled Etsy competition. Lower confidence is intentional where exact employment sizing or clean marketplace decomposition is unavailable. Дата: 2026-09-23 10:04:52.652496+00.
- **concept_depth**: 10.00 (confidence 0.800). Forge pool-completion provisional score using current BLS/O*NET evidence and sampled Etsy competition. Lower confidence is intentional where exact employment sizing or clean marketplace decomposition is unavailable. Дата: 2026-09-23 10:04:52.652496+00.
- **demand_evidence**: 4.50 (confidence 0.450). Forge pool-completion provisional score using current BLS/O*NET evidence and sampled Etsy competition. Lower confidence is intentional where exact employment sizing or clean marketplace decomposition is unavailable. Дата: 2026-09-23 10:04:52.652496+00.
- **founder_edge**: 2.00 (confidence 0.400). Forge pool-completion provisional score using current BLS/O*NET evidence and sampled Etsy competition. Lower confidence is intentional where exact employment sizing or clean marketplace decomposition is unavailable. Дата: 2026-09-23 10:04:52.652496+00.
- **identity_intensity**: 9.50 (confidence 0.760). Forge pool-completion provisional score using current BLS/O*NET evidence and sampled Etsy competition. Lower confidence is intentional where exact employment sizing or clean marketplace decomposition is unavailable. Дата: 2026-09-23 10:04:52.652496+00.
- **legal_safety**: 7.50 (confidence 0.580). Forge pool-completion provisional score using current BLS/O*NET evidence and sampled Etsy competition. Lower confidence is intentional where exact employment sizing or clean marketplace decomposition is unavailable. Дата: 2026-09-23 10:04:52.652496+00.
- **purchase_motivation**: 8.50 (confidence 0.700). Forge pool-completion provisional score using current BLS/O*NET evidence and sampled Etsy competition. Lower confidence is intentional where exact employment sizing or clean marketplace decomposition is unavailable. Дата: 2026-09-23 10:04:52.652496+00.
- **repeatability**: 8.00 (confidence 0.620). Forge pool-completion provisional score using current BLS/O*NET evidence and sampled Etsy competition. Lower confidence is intentional where exact employment sizing or clean marketplace decomposition is unavailable. Дата: 2026-09-23 10:04:52.652496+00.
- **visual_language**: 10.00 (confidence 0.840). Forge pool-completion provisional score using current BLS/O*NET evidence and sampled Etsy competition. Lower confidence is intentional where exact employment sizing or clean marketplace decomposition is unavailable. Дата: 2026-09-23 10:04:52.652496+00.

### Концепции (0)

## 05. Cardiovascular Technologist / Technician
Ключ: `cardiovascular_technologist` · ID: `e34da865-d6f0-4cb9-9ff9-eb54a9b62e39`

**Статус БД:** scored · **балл:** 75.05 · **confidence:** 66.22 · **coverage:** 100.00
**Аудитория:** Cardiovascular technologists and technicians
**Категория:** occupational_identity
**Исследовательская аргументация:** Medium-sized cardiovascular diagnostic/procedural occupation with strong technical identity and multiple sub-specialties. Needs marketplace decomposition because cardiac-sonography and broad cardiology merch can contaminate exact demand signals.
**Создано / обновлено:** 2026-09-23 10:00:20.805089+00 / 2026-09-23 10:04:52.652496+00

### Компоненты оценки ниши

- **channel_breadth**: 7.00 (confidence 0.560). Forge pool-completion provisional score using current BLS/O*NET evidence and sampled Etsy competition. Lower confidence is intentional where exact employment sizing or clean marketplace decomposition is unavailable. Дата: 2026-09-23 10:04:52.652496+00.
- **competition_opportunity**: 5.50 (confidence 0.460). Forge pool-completion provisional score using current BLS/O*NET evidence and sampled Etsy competition. Lower confidence is intentional where exact employment sizing or clean marketplace decomposition is unavailable. Дата: 2026-09-23 10:04:52.652496+00.
- **concept_depth**: 9.00 (confidence 0.680). Forge pool-completion provisional score using current BLS/O*NET evidence and sampled Etsy competition. Lower confidence is intentional where exact employment sizing or clean marketplace decomposition is unavailable. Дата: 2026-09-23 10:04:52.652496+00.
- **demand_evidence**: 7.50 (confidence 0.880). Forge pool-completion provisional score using current BLS/O*NET evidence and sampled Etsy competition. Lower confidence is intentional where exact employment sizing or clean marketplace decomposition is unavailable. Дата: 2026-09-23 10:04:52.652496+00.
- **founder_edge**: 2.00 (confidence 0.400). Forge pool-completion provisional score using current BLS/O*NET evidence and sampled Etsy competition. Lower confidence is intentional where exact employment sizing or clean marketplace decomposition is unavailable. Дата: 2026-09-23 10:04:52.652496+00.
- **identity_intensity**: 8.00 (confidence 0.660). Forge pool-completion provisional score using current BLS/O*NET evidence and sampled Etsy competition. Lower confidence is intentional where exact employment sizing or clean marketplace decomposition is unavailable. Дата: 2026-09-23 10:04:52.652496+00.
- **legal_safety**: 7.50 (confidence 0.580). Forge pool-completion provisional score using current BLS/O*NET evidence and sampled Etsy competition. Lower confidence is intentional where exact employment sizing or clean marketplace decomposition is unavailable. Дата: 2026-09-23 10:04:52.652496+00.
- **purchase_motivation**: 7.50 (confidence 0.620). Forge pool-completion provisional score using current BLS/O*NET evidence and sampled Etsy competition. Lower confidence is intentional where exact employment sizing or clean marketplace decomposition is unavailable. Дата: 2026-09-23 10:04:52.652496+00.
- **repeatability**: 8.00 (confidence 0.620). Forge pool-completion provisional score using current BLS/O*NET evidence and sampled Etsy competition. Lower confidence is intentional where exact employment sizing or clean marketplace decomposition is unavailable. Дата: 2026-09-23 10:04:52.652496+00.
- **visual_language**: 9.50 (confidence 0.740). Forge pool-completion provisional score using current BLS/O*NET evidence and sampled Etsy competition. Lower confidence is intentional where exact employment sizing or clean marketplace decomposition is unavailable. Дата: 2026-09-23 10:04:52.652496+00.

### Концепции (0)

## 06. Chemical Plant / System Operator
Ключ: `chemical_plant_operator` · ID: `72c39f24-d2f5-427d-a28f-11aefbeb68cd`

**Статус БД:** scored · **балл:** 72.05 · **confidence:** 63.92 · **coverage:** 100.00
**Аудитория:** Chemical plant and system operators
**Категория:** occupational_identity
**Исследовательская аргументация:** Small process-operations occupation with excellent control-room/process visual language, but projected employment is declining. Retained as a process-industry benchmark and possible insider micro-niche.
**Создано / обновлено:** 2026-09-23 10:00:20.805089+00 / 2026-09-23 10:04:52.652496+00

### Компоненты оценки ниши

- **channel_breadth**: 6.50 (confidence 0.500). Forge pool-completion provisional score using current BLS/O*NET evidence and sampled Etsy competition. Lower confidence is intentional where exact employment sizing or clean marketplace decomposition is unavailable. Дата: 2026-09-23 10:04:52.652496+00.
- **competition_opportunity**: 8.50 (confidence 0.500). Forge pool-completion provisional score using current BLS/O*NET evidence and sampled Etsy competition. Lower confidence is intentional where exact employment sizing or clean marketplace decomposition is unavailable. Дата: 2026-09-23 10:04:52.652496+00.
- **concept_depth**: 8.50 (confidence 0.640). Forge pool-completion provisional score using current BLS/O*NET evidence and sampled Etsy competition. Lower confidence is intentional where exact employment sizing or clean marketplace decomposition is unavailable. Дата: 2026-09-23 10:04:52.652496+00.
- **demand_evidence**: 5.30 (confidence 0.900). Forge pool-completion provisional score using current BLS/O*NET evidence and sampled Etsy competition. Lower confidence is intentional where exact employment sizing or clean marketplace decomposition is unavailable. Дата: 2026-09-23 10:04:52.652496+00.
- **founder_edge**: 2.00 (confidence 0.400). Forge pool-completion provisional score using current BLS/O*NET evidence and sampled Etsy competition. Lower confidence is intentional where exact employment sizing or clean marketplace decomposition is unavailable. Дата: 2026-09-23 10:04:52.652496+00.
- **identity_intensity**: 7.50 (confidence 0.600). Forge pool-completion provisional score using current BLS/O*NET evidence and sampled Etsy competition. Lower confidence is intentional where exact employment sizing or clean marketplace decomposition is unavailable. Дата: 2026-09-23 10:04:52.652496+00.
- **legal_safety**: 8.00 (confidence 0.580). Forge pool-completion provisional score using current BLS/O*NET evidence and sampled Etsy competition. Lower confidence is intentional where exact employment sizing or clean marketplace decomposition is unavailable. Дата: 2026-09-23 10:04:52.652496+00.
- **purchase_motivation**: 7.00 (confidence 0.560). Forge pool-completion provisional score using current BLS/O*NET evidence and sampled Etsy competition. Lower confidence is intentional where exact employment sizing or clean marketplace decomposition is unavailable. Дата: 2026-09-23 10:04:52.652496+00.
- **repeatability**: 7.00 (confidence 0.540). Forge pool-completion provisional score using current BLS/O*NET evidence and sampled Etsy competition. Lower confidence is intentional where exact employment sizing or clean marketplace decomposition is unavailable. Дата: 2026-09-23 10:04:52.652496+00.
- **visual_language**: 9.00 (confidence 0.700). Forge pool-completion provisional score using current BLS/O*NET evidence and sampled Etsy competition. Lower confidence is intentional where exact employment sizing or clean marketplace decomposition is unavailable. Дата: 2026-09-23 10:04:52.652496+00.

### Концепции (0)

## 07. Chemical Technician
Ключ: `chemical_technician` · ID: `2824041a-b8fb-4c03-a745-197c7ebf7c18`

**Статус БД:** scored · **балл:** 76.50 · **confidence:** 63.82 · **coverage:** 100.00
**Аудитория:** Chemical laboratory, manufacturing-process and QC technicians
**Категория:** occupational_identity
**Исследовательская аргументация:** Mid-sized technical occupation combining laboratory analysis, manufacturing-process monitoring, testing and quality control. Strong original visual language from glassware, samples, process data and instrumentation; sampled exact Etsy search did not surface a dedicated Chemical Technician shirt category.
**Создано / обновлено:** 2026-09-23 09:56:40.513406+00 / 2026-09-23 09:56:40.513406+00

### Компоненты оценки ниши

- **channel_breadth**: 8.00 (confidence 0.600). Forge diversity-batch v3 score using current 2025-35 BLS/O*NET evidence plus sampled current Etsy competition. Where exact marketplace counts were unavailable, competition confidence is intentionally lower. Дата: 2026-09-23 09:56:40.513406+00.
- **competition_opportunity**: 8.50 (confidence 0.480). Forge diversity-batch v3 score using current 2025-35 BLS/O*NET evidence plus sampled current Etsy competition. Where exact marketplace counts were unavailable, competition confidence is intentionally lower. Дата: 2026-09-23 09:56:40.513406+00.
- **concept_depth**: 8.50 (confidence 0.680). Forge diversity-batch v3 score using current 2025-35 BLS/O*NET evidence plus sampled current Etsy competition. Where exact marketplace counts were unavailable, competition confidence is intentionally lower. Дата: 2026-09-23 09:56:40.513406+00.
- **demand_evidence**: 8.00 (confidence 0.880). Forge diversity-batch v3 score using current 2025-35 BLS/O*NET evidence plus sampled current Etsy competition. Where exact marketplace counts were unavailable, competition confidence is intentionally lower. Дата: 2026-09-23 09:56:40.513406+00.
- **founder_edge**: 2.00 (confidence 0.400). Forge diversity-batch v3 score using current 2025-35 BLS/O*NET evidence plus sampled current Etsy competition. Where exact marketplace counts were unavailable, competition confidence is intentionally lower. Дата: 2026-09-23 09:56:40.513406+00.
- **identity_intensity**: 6.50 (confidence 0.560). Forge diversity-batch v3 score using current 2025-35 BLS/O*NET evidence plus sampled current Etsy competition. Where exact marketplace counts were unavailable, competition confidence is intentionally lower. Дата: 2026-09-23 09:56:40.513406+00.
- **legal_safety**: 9.00 (confidence 0.680). Forge diversity-batch v3 score using current 2025-35 BLS/O*NET evidence plus sampled current Etsy competition. Where exact marketplace counts were unavailable, competition confidence is intentionally lower. Дата: 2026-09-23 09:56:40.513406+00.
- **purchase_motivation**: 6.50 (confidence 0.520). Forge diversity-batch v3 score using current 2025-35 BLS/O*NET evidence plus sampled current Etsy competition. Where exact marketplace counts were unavailable, competition confidence is intentionally lower. Дата: 2026-09-23 09:56:40.513406+00.
- **repeatability**: 7.50 (confidence 0.580). Forge diversity-batch v3 score using current 2025-35 BLS/O*NET evidence plus sampled current Etsy competition. Where exact marketplace counts were unavailable, competition confidence is intentionally lower. Дата: 2026-09-23 09:56:40.513406+00.
- **visual_language**: 9.00 (confidence 0.740). Forge diversity-batch v3 score using current 2025-35 BLS/O*NET evidence plus sampled current Etsy competition. Where exact marketplace counts were unavailable, competition confidence is intentionally lower. Дата: 2026-09-23 09:56:40.513406+00.

### Концепции (0)

## 08. Civil Engineering Technologist / Technician
Ключ: `civil_engineering_technologist_technician` · ID: `58608283-b662-4461-afdf-290813a3d438`

**Статус БД:** scored · **балл:** 76.85 · **confidence:** 64.90 · **coverage:** 100.00
**Аудитория:** Civil engineering technologists and technicians supporting infrastructure projects
**Категория:** occupational_identity
**Исследовательская аргументация:** Large enough infrastructure-support occupation with roads, bridges, drainage, survey/layout, testing and construction-document visual language. Marketplace appears fragmented into generic civil-engineering merch rather than exact technician identity.
**Создано / обновлено:** 2026-09-23 09:56:40.513406+00 / 2026-09-23 09:56:40.513406+00

### Компоненты оценки ниши

- **channel_breadth**: 8.00 (confidence 0.620). Forge diversity-batch v3 score using current 2025-35 BLS/O*NET evidence plus sampled current Etsy competition. Where exact marketplace counts were unavailable, competition confidence is intentionally lower. Дата: 2026-09-23 09:56:40.513406+00.
- **competition_opportunity**: 7.50 (confidence 0.480). Forge diversity-batch v3 score using current 2025-35 BLS/O*NET evidence plus sampled current Etsy competition. Where exact marketplace counts were unavailable, competition confidence is intentionally lower. Дата: 2026-09-23 09:56:40.513406+00.
- **concept_depth**: 8.50 (confidence 0.680). Forge diversity-batch v3 score using current 2025-35 BLS/O*NET evidence plus sampled current Etsy competition. Where exact marketplace counts were unavailable, competition confidence is intentionally lower. Дата: 2026-09-23 09:56:40.513406+00.
- **demand_evidence**: 8.00 (confidence 0.900). Forge diversity-batch v3 score using current 2025-35 BLS/O*NET evidence plus sampled current Etsy competition. Where exact marketplace counts were unavailable, competition confidence is intentionally lower. Дата: 2026-09-23 09:56:40.513406+00.
- **founder_edge**: 2.00 (confidence 0.400). Forge diversity-batch v3 score using current 2025-35 BLS/O*NET evidence plus sampled current Etsy competition. Where exact marketplace counts were unavailable, competition confidence is intentionally lower. Дата: 2026-09-23 09:56:40.513406+00.
- **identity_intensity**: 7.50 (confidence 0.600). Forge diversity-batch v3 score using current 2025-35 BLS/O*NET evidence plus sampled current Etsy competition. Where exact marketplace counts were unavailable, competition confidence is intentionally lower. Дата: 2026-09-23 09:56:40.513406+00.
- **legal_safety**: 9.00 (confidence 0.680). Forge diversity-batch v3 score using current 2025-35 BLS/O*NET evidence plus sampled current Etsy competition. Where exact marketplace counts were unavailable, competition confidence is intentionally lower. Дата: 2026-09-23 09:56:40.513406+00.
- **purchase_motivation**: 7.00 (confidence 0.540). Forge diversity-batch v3 score using current 2025-35 BLS/O*NET evidence plus sampled current Etsy competition. Where exact marketplace counts were unavailable, competition confidence is intentionally lower. Дата: 2026-09-23 09:56:40.513406+00.
- **repeatability**: 7.50 (confidence 0.580). Forge diversity-batch v3 score using current 2025-35 BLS/O*NET evidence plus sampled current Etsy competition. Where exact marketplace counts were unavailable, competition confidence is intentionally lower. Дата: 2026-09-23 09:56:40.513406+00.
- **visual_language**: 8.50 (confidence 0.700). Forge diversity-batch v3 score using current 2025-35 BLS/O*NET evidence plus sampled current Etsy competition. Where exact marketplace counts were unavailable, competition confidence is intentionally lower. Дата: 2026-09-23 09:56:40.513406+00.

### Концепции (0)

## 09. CNC Machinist
Ключ: `cnc_machinist` · ID: `00f957d4-9e11-4a23-9ae3-6642877cef1d`

**Статус БД:** scored · **балл:** 79.10 · **confidence:** 81.46 · **coverage:** 100.00
**Аудитория:** Machinists and CNC machine-tool operators/programmers
**Категория:** occupational_identity
**Исследовательская аргументация:** Very large replacement-driven occupation with rich manufacturing language, but generic machinist/CNC merch likely competitive; retained for later evidence-based comparison.
**Создано / обновлено:** 2026-09-23 09:34:00.70472+00 / 2026-09-23 09:57:21.800356+00

### Компоненты оценки ниши

- **channel_breadth**: 8.50 (confidence 0.680). Current BLS shows 288,300 machinists / 344,900 machinists+tool-die combined and 30,400 annual combined replacement openings; Etsy sampled 315+ CNC Machinist Shirt and 601+ broader Machinists Tee Shirt items, so demand is strong but whitespace receives a substantial penalty. Дата: 2026-09-23 09:57:21.800356+00.
- **competition_opportunity**: 4.00 (confidence 0.900). Current BLS shows 288,300 machinists / 344,900 machinists+tool-die combined and 30,400 annual combined replacement openings; Etsy sampled 315+ CNC Machinist Shirt and 601+ broader Machinists Tee Shirt items, so demand is strong but whitespace receives a substantial penalty. Дата: 2026-09-23 09:57:21.800356+00.
- **concept_depth**: 9.00 (confidence 0.780). Current BLS shows 288,300 machinists / 344,900 machinists+tool-die combined and 30,400 annual combined replacement openings; Etsy sampled 315+ CNC Machinist Shirt and 601+ broader Machinists Tee Shirt items, so demand is strong but whitespace receives a substantial penalty. Дата: 2026-09-23 09:57:21.800356+00.
- **demand_evidence**: 8.50 (confidence 0.940). Current BLS shows 288,300 machinists / 344,900 machinists+tool-die combined and 30,400 annual combined replacement openings; Etsy sampled 315+ CNC Machinist Shirt and 601+ broader Machinists Tee Shirt items, so demand is strong but whitespace receives a substantial penalty. Дата: 2026-09-23 09:57:21.800356+00.
- **founder_edge**: 2.00 (confidence 0.400). Current BLS shows 288,300 machinists / 344,900 machinists+tool-die combined and 30,400 annual combined replacement openings; Etsy sampled 315+ CNC Machinist Shirt and 601+ broader Machinists Tee Shirt items, so demand is strong but whitespace receives a substantial penalty. Дата: 2026-09-23 09:57:21.800356+00.
- **identity_intensity**: 9.00 (confidence 0.800). Current BLS shows 288,300 machinists / 344,900 machinists+tool-die combined and 30,400 annual combined replacement openings; Etsy sampled 315+ CNC Machinist Shirt and 601+ broader Machinists Tee Shirt items, so demand is strong but whitespace receives a substantial penalty. Дата: 2026-09-23 09:57:21.800356+00.
- **legal_safety**: 8.50 (confidence 0.680). Current BLS shows 288,300 machinists / 344,900 machinists+tool-die combined and 30,400 annual combined replacement openings; Etsy sampled 315+ CNC Machinist Shirt and 601+ broader Machinists Tee Shirt items, so demand is strong but whitespace receives a substantial penalty. Дата: 2026-09-23 09:57:21.800356+00.
- **purchase_motivation**: 8.50 (confidence 0.760). Current BLS shows 288,300 machinists / 344,900 machinists+tool-die combined and 30,400 annual combined replacement openings; Etsy sampled 315+ CNC Machinist Shirt and 601+ broader Machinists Tee Shirt items, so demand is strong but whitespace receives a substantial penalty. Дата: 2026-09-23 09:57:21.800356+00.
- **repeatability**: 8.50 (confidence 0.720). Current BLS shows 288,300 machinists / 344,900 machinists+tool-die combined and 30,400 annual combined replacement openings; Etsy sampled 315+ CNC Machinist Shirt and 601+ broader Machinists Tee Shirt items, so demand is strong but whitespace receives a substantial penalty. Дата: 2026-09-23 09:57:21.800356+00.
- **visual_language**: 9.50 (confidence 0.820). Current BLS shows 288,300 machinists / 344,900 machinists+tool-die combined and 30,400 annual combined replacement openings; Etsy sampled 315+ CNC Machinist Shirt and 601+ broader Machinists Tee Shirt items, so demand is strong but whitespace receives a substantial penalty. Дата: 2026-09-23 09:57:21.800356+00.

### Концепции (6)

#### CNC — CAD/CAM to inspection
`cnc_cadcam_setup_machine_inspect` · ID `9a7960ed-a33b-43b3-b0a8-e637c805a7c9`

**Интерпретация:** Исследовательский кандидат; одобрение владельца не зафиксировано
**Статус БД:** scored · **балл:** 87.67 · **confidence:** 68.17 · **coverage:** 100.00
**Текст / хук:** CAD/CAM → SETUP → MACHINE → INSPECT
**Идея:** CNC — CAD/CAM to inspection. Core hook: CAD/CAM → SETUP → MACHINE → INSPECT. Grounded in current occupational tasks and intended as insider identity art, not operating/medical instruction. Avoid employer, OEM, certification-body and proprietary-interface branding.
**Покупатель:** CNC machinists
**Причина покупки:** Professional identity purchase for cnc machinists who recognize the real tools, measurements and workflow.
**Отличие:** Technical process direction designed to avoid generic job-title, floral, retro-badge and parody templates.
**Визуальное направление:** Digital-to-physical manufacturing workflow with original CAD/toolpath/machine/inspection motifs.
**Создано / обновлено:** 2026-09-23 10:02:18.463532+00 / 2026-09-23 10:02:33.245254+00

Компоненты оценки:
- **buyer_desire**: 8.43 (confidence 0.670). Provisional Forge challenger-concept score derived from occupationally grounded concept archetype plus the fully scored niche prior. It is a research-priority score, not a sales forecast or legal clearance. Дата: 2026-09-23 10:02:33.245254+00.
- **clarity_at_glance**: 8.80 (confidence 0.670). Provisional Forge challenger-concept score derived from occupationally grounded concept archetype plus the fully scored niche prior. It is a research-priority score, not a sales forecast or legal clearance. Дата: 2026-09-23 10:02:33.245254+00.
- **distinctiveness**: 8.80 (confidence 0.670). Provisional Forge challenger-concept score derived from occupationally grounded concept archetype plus the fully scored niche prior. It is a research-priority score, not a sales forecast or legal clearance. Дата: 2026-09-23 10:02:33.245254+00.
- **giftability**: 7.90 (confidence 0.670). Provisional Forge challenger-concept score derived from occupationally grounded concept archetype plus the fully scored niche prior. It is a research-priority score, not a sales forecast or legal clearance. Дата: 2026-09-23 10:02:33.245254+00.
- **insider_resonance**: 9.15 (confidence 0.700). Provisional Forge challenger-concept score derived from occupationally grounded concept archetype plus the fully scored niche prior. It is a research-priority score, not a sales forecast or legal clearance. Дата: 2026-09-23 10:02:33.245254+00.
- **ip_safety**: 8.80 (confidence 0.670). Provisional Forge challenger-concept score derived from occupationally grounded concept archetype plus the fully scored niche prior. It is a research-priority score, not a sales forecast or legal clearance. Дата: 2026-09-23 10:02:33.245254+00.
- **niche_fit**: 9.32 (confidence 0.700). Provisional Forge challenger-concept score derived from occupationally grounded concept archetype plus the fully scored niche prior. It is a research-priority score, not a sales forecast or legal clearance. Дата: 2026-09-23 10:02:33.245254+00.
- **visual_potential**: 8.95 (confidence 0.700). Provisional Forge challenger-concept score derived from occupationally grounded concept archetype plus the fully scored niche prior. It is a research-priority score, not a sales forecast or legal clearance. Дата: 2026-09-23 10:02:33.245254+00.

#### CNC — drawing to verified part
`cnc_drawing_setup_cut_verify` · ID `a16dbb37-770c-4f7a-b1c6-de986dbe900d`

**Интерпретация:** Исследовательский кандидат; одобрение владельца не зафиксировано
**Статус БД:** scored · **балл:** 86.18 · **confidence:** 67.17 · **coverage:** 100.00
**Текст / хук:** DRAWING → SETUP → CUT → VERIFY
**Идея:** CNC — drawing to verified part. Core hook: DRAWING → SETUP → CUT → VERIFY. Grounded in current occupational tasks and intended as insider identity art, not operating/medical instruction. Avoid employer, OEM, certification-body and proprietary-interface branding.
**Покупатель:** CNC machinists
**Причина покупки:** Professional identity purchase for cnc machinists who recognize the real tools, measurements and workflow.
**Отличие:** Technical workflow direction designed to avoid generic job-title, floral, retro-badge and parody templates.
**Визуальное направление:** Machining workflow from engineering drawing through setup/machining to dimensional verification.
**Создано / обновлено:** 2026-09-23 10:02:18.463532+00 / 2026-09-23 10:02:33.245254+00

Компоненты оценки:
- **buyer_desire**: 8.33 (confidence 0.660). Provisional Forge challenger-concept score derived from occupationally grounded concept archetype plus the fully scored niche prior. It is a research-priority score, not a sales forecast or legal clearance. Дата: 2026-09-23 10:02:33.245254+00.
- **clarity_at_glance**: 9.20 (confidence 0.660). Provisional Forge challenger-concept score derived from occupationally grounded concept archetype plus the fully scored niche prior. It is a research-priority score, not a sales forecast or legal clearance. Дата: 2026-09-23 10:02:33.245254+00.
- **distinctiveness**: 8.50 (confidence 0.660). Provisional Forge challenger-concept score derived from occupationally grounded concept archetype plus the fully scored niche prior. It is a research-priority score, not a sales forecast or legal clearance. Дата: 2026-09-23 10:02:33.245254+00.
- **giftability**: 8.10 (confidence 0.660). Provisional Forge challenger-concept score derived from occupationally grounded concept archetype plus the fully scored niche prior. It is a research-priority score, not a sales forecast or legal clearance. Дата: 2026-09-23 10:02:33.245254+00.
- **insider_resonance**: 8.85 (confidence 0.690). Provisional Forge challenger-concept score derived from occupationally grounded concept archetype plus the fully scored niche prior. It is a research-priority score, not a sales forecast or legal clearance. Дата: 2026-09-23 10:02:33.245254+00.
- **ip_safety**: 9.00 (confidence 0.660). Provisional Forge challenger-concept score derived from occupationally grounded concept archetype plus the fully scored niche prior. It is a research-priority score, not a sales forecast or legal clearance. Дата: 2026-09-23 10:02:33.245254+00.
- **niche_fit**: 9.22 (confidence 0.690). Provisional Forge challenger-concept score derived from occupationally grounded concept archetype plus the fully scored niche prior. It is a research-priority score, not a sales forecast or legal clearance. Дата: 2026-09-23 10:02:33.245254+00.
- **visual_potential**: 8.45 (confidence 0.690). Provisional Forge challenger-concept score derived from occupationally grounded concept archetype plus the fully scored niche prior. It is a research-priority score, not a sales forecast or legal clearance. Дата: 2026-09-23 10:02:33.245254+00.

#### CNC — measure / tolerance / finish / pass
`cnc_measure_tolerance_finish_pass` · ID `d2d7ba3f-b56c-4208-8bef-83efaa98211a`

**Интерпретация:** Исследовательский кандидат; одобрение владельца не зафиксировано
**Статус БД:** scored · **балл:** 88.66 · **confidence:** 69.17 · **coverage:** 100.00
**Текст / хук:** MEASURE • TOLERANCE • FINISH • PASS
**Идея:** CNC — measure / tolerance / finish / pass. Core hook: MEASURE • TOLERANCE • FINISH • PASS. Grounded in current occupational tasks and intended as insider identity art, not operating/medical instruction. Avoid employer, OEM, certification-body and proprietary-interface branding.
**Покупатель:** CNC machinists
**Причина покупки:** Professional identity purchase for cnc machinists who recognize the real tools, measurements and workflow.
**Отличие:** Technical diagnostic direction designed to avoid generic job-title, floral, retro-badge and parody templates.
**Визуальное направление:** Quality-control machinist identity with caliper/gauge and tolerance-band visual language.
**Создано / обновлено:** 2026-09-23 10:02:18.463532+00 / 2026-09-23 10:15:01.390702+00

Компоненты оценки:
- **buyer_desire**: 8.63 (confidence 0.680). Provisional Forge challenger-concept score derived from occupationally grounded concept archetype plus the fully scored niche prior. It is a research-priority score, not a sales forecast or legal clearance. Дата: 2026-09-23 10:02:33.245254+00.
- **clarity_at_glance**: 8.57 (confidence 0.680). Provisional Forge challenger-concept score derived from occupationally grounded concept archetype plus the fully scored niche prior. It is a research-priority score, not a sales forecast or legal clearance. Дата: 2026-09-23 10:02:33.245254+00.
- **distinctiveness**: 9.00 (confidence 0.680). Provisional Forge challenger-concept score derived from occupationally grounded concept archetype plus the fully scored niche prior. It is a research-priority score, not a sales forecast or legal clearance. Дата: 2026-09-23 10:02:33.245254+00.
- **giftability**: 7.87 (confidence 0.680). Provisional Forge challenger-concept score derived from occupationally grounded concept archetype plus the fully scored niche prior. It is a research-priority score, not a sales forecast or legal clearance. Дата: 2026-09-23 10:02:33.245254+00.
- **insider_resonance**: 9.40 (confidence 0.710). Provisional Forge challenger-concept score derived from occupationally grounded concept archetype plus the fully scored niche prior. It is a research-priority score, not a sales forecast or legal clearance. Дата: 2026-09-23 10:02:33.245254+00.
- **ip_safety**: 8.70 (confidence 0.680). Provisional Forge challenger-concept score derived from occupationally grounded concept archetype plus the fully scored niche prior. It is a research-priority score, not a sales forecast or legal clearance. Дата: 2026-09-23 10:02:33.245254+00.
- **niche_fit**: 9.42 (confidence 0.710). Provisional Forge challenger-concept score derived from occupationally grounded concept archetype plus the fully scored niche prior. It is a research-priority score, not a sales forecast or legal clearance. Дата: 2026-09-23 10:02:33.245254+00.
- **visual_potential**: 8.90 (confidence 0.710). Provisional Forge challenger-concept score derived from occupationally grounded concept archetype plus the fully scored niche prior. It is a research-priority score, not a sales forecast or legal clearance. Дата: 2026-09-23 10:02:33.245254+00.

#### CNC — process family
`cnc_turn_mill_drill_grind` · ID `34300050-b515-4655-977a-dbe54fc37ade`

**Интерпретация:** Исследовательский кандидат; одобрение владельца не зафиксировано
**Статус БД:** scored · **балл:** 86.91 · **confidence:** 67.17 · **coverage:** 100.00
**Текст / хук:** TURN • MILL • DRILL • GRIND
**Идея:** CNC — process family. Core hook: TURN • MILL • DRILL • GRIND. Grounded in current occupational tasks and intended as insider identity art, not operating/medical instruction. Avoid employer, OEM, certification-body and proprietary-interface branding.
**Покупатель:** CNC machinists
**Причина покупки:** Professional identity purchase for cnc machinists who recognize the real tools, measurements and workflow.
**Отличие:** Technical terminology direction designed to avoid generic job-title, floral, retro-badge and parody templates.
**Визуальное направление:** Four machining operations presented as original process icons and geometry.
**Создано / обновлено:** 2026-09-23 10:02:18.463532+00 / 2026-09-23 10:02:33.245254+00

Компоненты оценки:
- **buyer_desire**: 8.03 (confidence 0.660). Provisional Forge challenger-concept score derived from occupationally grounded concept archetype plus the fully scored niche prior. It is a research-priority score, not a sales forecast or legal clearance. Дата: 2026-09-23 10:02:33.245254+00.
- **clarity_at_glance**: 9.27 (confidence 0.660). Provisional Forge challenger-concept score derived from occupationally grounded concept archetype plus the fully scored niche prior. It is a research-priority score, not a sales forecast or legal clearance. Дата: 2026-09-23 10:02:33.245254+00.
- **distinctiveness**: 8.50 (confidence 0.660). Provisional Forge challenger-concept score derived from occupationally grounded concept archetype plus the fully scored niche prior. It is a research-priority score, not a sales forecast or legal clearance. Дата: 2026-09-23 10:02:33.245254+00.
- **giftability**: 8.17 (confidence 0.660). Provisional Forge challenger-concept score derived from occupationally grounded concept archetype plus the fully scored niche prior. It is a research-priority score, not a sales forecast or legal clearance. Дата: 2026-09-23 10:02:33.245254+00.
- **insider_resonance**: 9.50 (confidence 0.690). Provisional Forge challenger-concept score derived from occupationally grounded concept archetype plus the fully scored niche prior. It is a research-priority score, not a sales forecast or legal clearance. Дата: 2026-09-23 10:02:33.245254+00.
- **ip_safety**: 8.80 (confidence 0.660). Provisional Forge challenger-concept score derived from occupationally grounded concept archetype plus the fully scored niche prior. It is a research-priority score, not a sales forecast or legal clearance. Дата: 2026-09-23 10:02:33.245254+00.
- **niche_fit**: 9.42 (confidence 0.690). Provisional Forge challenger-concept score derived from occupationally grounded concept archetype plus the fully scored niche prior. It is a research-priority score, not a sales forecast or legal clearance. Дата: 2026-09-23 10:02:33.245254+00.
- **visual_potential**: 8.50 (confidence 0.690). Provisional Forge challenger-concept score derived from occupationally grounded concept archetype plus the fully scored niche prior. It is a research-priority score, not a sales forecast or legal clearance. Дата: 2026-09-23 10:02:33.245254+00.

#### CNC — workpiece / tool / speed / feed
`cnc_workpiece_tool_speed_feed` · ID `9dea3f6c-e02d-4206-93e5-7ae328bd937e`

**Интерпретация:** Исследовательский кандидат; одобрение владельца не зафиксировано
**Статус БД:** scored · **балл:** 88.08 · **confidence:** 69.17 · **coverage:** 100.00
**Текст / хук:** WORKPIECE • TOOL • SPEED • FEED
**Идея:** CNC — workpiece / tool / speed / feed. Core hook: WORKPIECE • TOOL • SPEED • FEED. Grounded in current occupational tasks and intended as insider identity art, not operating/medical instruction. Avoid employer, OEM, certification-body and proprietary-interface branding.
**Покупатель:** CNC machinists
**Причина покупки:** Professional identity purchase for cnc machinists who recognize the real tools, measurements and workflow.
**Отличие:** Technical system map direction designed to avoid generic job-title, floral, retro-badge and parody templates.
**Визуальное направление:** Machining-system identity using high-level variables only; no cutting parameter values.
**Создано / обновлено:** 2026-09-23 10:02:18.463532+00 / 2026-09-23 10:03:30.159451+00

Компоненты оценки:
- **buyer_desire**: 8.43 (confidence 0.680). Provisional Forge challenger-concept score derived from occupationally grounded concept archetype plus the fully scored niche prior. It is a research-priority score, not a sales forecast or legal clearance. Дата: 2026-09-23 10:02:33.245254+00.
- **clarity_at_glance**: 8.17 (confidence 0.680). Provisional Forge challenger-concept score derived from occupationally grounded concept archetype plus the fully scored niche prior. It is a research-priority score, not a sales forecast or legal clearance. Дата: 2026-09-23 10:02:33.245254+00.
- **distinctiveness**: 9.00 (confidence 0.680). Provisional Forge challenger-concept score derived from occupationally grounded concept archetype plus the fully scored niche prior. It is a research-priority score, not a sales forecast or legal clearance. Дата: 2026-09-23 10:02:33.245254+00.
- **giftability**: 7.57 (confidence 0.680). Provisional Forge challenger-concept score derived from occupationally grounded concept archetype plus the fully scored niche prior. It is a research-priority score, not a sales forecast or legal clearance. Дата: 2026-09-23 10:02:33.245254+00.
- **insider_resonance**: 9.10 (confidence 0.710). Provisional Forge challenger-concept score derived from occupationally grounded concept archetype plus the fully scored niche prior. It is a research-priority score, not a sales forecast or legal clearance. Дата: 2026-09-23 10:02:33.245254+00.
- **ip_safety**: 8.80 (confidence 0.680). Provisional Forge challenger-concept score derived from occupationally grounded concept archetype plus the fully scored niche prior. It is a research-priority score, not a sales forecast or legal clearance. Дата: 2026-09-23 10:02:33.245254+00.
- **niche_fit**: 9.32 (confidence 0.710). Provisional Forge challenger-concept score derived from occupationally grounded concept archetype plus the fully scored niche prior. It is a research-priority score, not a sales forecast or legal clearance. Дата: 2026-09-23 10:02:33.245254+00.
- **visual_potential**: 9.60 (confidence 0.710). Provisional Forge challenger-concept score derived from occupationally grounded concept archetype plus the fully scored niche prior. It is a research-priority score, not a sales forecast or legal clearance. Дата: 2026-09-23 10:02:33.245254+00.

#### CNC — zero / offset / tool / tolerance
`cnc_zero_offset_tool_tolerance` · ID `df53ec5f-ed39-4ba9-9a10-5f1fe5870696`

**Интерпретация:** Исследовательский кандидат; одобрение владельца не зафиксировано
**Статус БД:** scored · **балл:** 87.52 · **confidence:** 67.17 · **coverage:** 100.00
**Текст / хук:** ZERO • OFFSET • TOOL • TOLERANCE
**Идея:** CNC — zero / offset / tool / tolerance. Core hook: ZERO • OFFSET • TOOL • TOLERANCE. Grounded in current occupational tasks and intended as insider identity art, not operating/medical instruction. Avoid employer, OEM, certification-body and proprietary-interface branding.
**Покупатель:** CNC machinists
**Причина покупки:** Professional identity purchase for cnc machinists who recognize the real tools, measurements and workflow.
**Отличие:** Technical terminology direction designed to avoid generic job-title, floral, retro-badge and parody templates.
**Визуальное направление:** Machinist insider vocabulary with original coordinate/tool-offset geometry; not machine-operation instruction.
**Создано / обновлено:** 2026-09-23 10:02:18.463532+00 / 2026-09-23 10:02:33.245254+00

Компоненты оценки:
- **buyer_desire**: 8.13 (confidence 0.660). Provisional Forge challenger-concept score derived from occupationally grounded concept archetype plus the fully scored niche prior. It is a research-priority score, not a sales forecast or legal clearance. Дата: 2026-09-23 10:02:33.245254+00.
- **clarity_at_glance**: 9.30 (confidence 0.660). Provisional Forge challenger-concept score derived from occupationally grounded concept archetype plus the fully scored niche prior. It is a research-priority score, not a sales forecast or legal clearance. Дата: 2026-09-23 10:02:33.245254+00.
- **distinctiveness**: 8.60 (confidence 0.660). Provisional Forge challenger-concept score derived from occupationally grounded concept archetype plus the fully scored niche prior. It is a research-priority score, not a sales forecast or legal clearance. Дата: 2026-09-23 10:02:33.245254+00.
- **giftability**: 8.20 (confidence 0.660). Provisional Forge challenger-concept score derived from occupationally grounded concept archetype plus the fully scored niche prior. It is a research-priority score, not a sales forecast or legal clearance. Дата: 2026-09-23 10:02:33.245254+00.
- **insider_resonance**: 9.55 (confidence 0.690). Provisional Forge challenger-concept score derived from occupationally grounded concept archetype plus the fully scored niche prior. It is a research-priority score, not a sales forecast or legal clearance. Дата: 2026-09-23 10:02:33.245254+00.
- **ip_safety**: 8.80 (confidence 0.660). Provisional Forge challenger-concept score derived from occupationally grounded concept archetype plus the fully scored niche prior. It is a research-priority score, not a sales forecast or legal clearance. Дата: 2026-09-23 10:02:33.245254+00.
- **niche_fit**: 9.42 (confidence 0.690). Provisional Forge challenger-concept score derived from occupationally grounded concept archetype plus the fully scored niche prior. It is a research-priority score, not a sales forecast or legal clearance. Дата: 2026-09-23 10:02:33.245254+00.
- **visual_potential**: 8.55 (confidence 0.690). Provisional Forge challenger-concept score derived from occupationally grounded concept archetype plus the fully scored niche prior. It is a research-priority score, not a sales forecast or legal clearance. Дата: 2026-09-23 10:02:33.245254+00.

## 10. Control & Valve Installer / Repairer
Ключ: `control_valve_repairer` · ID: `09b0db6a-2264-413d-bb79-fbc11adea9f4`

**Статус БД:** scored · **балл:** 77.95 · **confidence:** 63.98 · **coverage:** 100.00
**Аудитория:** Industrial and utility control-valve installers and repairers
**Категория:** occupational_identity
**Исследовательская аргументация:** Mid-sized technical maintenance occupation with strong visual language around regulating devices, valves, meters, governors, actuators and flow control. Potentially adjacent to I&C but more mechanical/service-focused.
**Создано / обновлено:** 2026-09-23 10:00:20.805089+00 / 2026-09-23 10:04:52.652496+00

### Компоненты оценки ниши

- **channel_breadth**: 7.00 (confidence 0.520). Forge pool-completion provisional score using current BLS/O*NET evidence and sampled Etsy competition. Lower confidence is intentional where exact employment sizing or clean marketplace decomposition is unavailable. Дата: 2026-09-23 10:04:52.652496+00.
- **competition_opportunity**: 8.50 (confidence 0.520). Forge pool-completion provisional score using current BLS/O*NET evidence and sampled Etsy competition. Lower confidence is intentional where exact employment sizing or clean marketplace decomposition is unavailable. Дата: 2026-09-23 10:04:52.652496+00.
- **concept_depth**: 9.00 (confidence 0.660). Forge pool-completion provisional score using current BLS/O*NET evidence and sampled Etsy competition. Lower confidence is intentional where exact employment sizing or clean marketplace decomposition is unavailable. Дата: 2026-09-23 10:04:52.652496+00.
- **demand_evidence**: 7.30 (confidence 0.820). Forge pool-completion provisional score using current BLS/O*NET evidence and sampled Etsy competition. Lower confidence is intentional where exact employment sizing or clean marketplace decomposition is unavailable. Дата: 2026-09-23 10:04:52.652496+00.
- **founder_edge**: 2.00 (confidence 0.400). Forge pool-completion provisional score using current BLS/O*NET evidence and sampled Etsy competition. Lower confidence is intentional where exact employment sizing or clean marketplace decomposition is unavailable. Дата: 2026-09-23 10:04:52.652496+00.
- **identity_intensity**: 7.50 (confidence 0.620). Forge pool-completion provisional score using current BLS/O*NET evidence and sampled Etsy competition. Lower confidence is intentional where exact employment sizing or clean marketplace decomposition is unavailable. Дата: 2026-09-23 10:04:52.652496+00.
- **legal_safety**: 8.50 (confidence 0.600). Forge pool-completion provisional score using current BLS/O*NET evidence and sampled Etsy competition. Lower confidence is intentional where exact employment sizing or clean marketplace decomposition is unavailable. Дата: 2026-09-23 10:04:52.652496+00.
- **purchase_motivation**: 7.00 (confidence 0.580). Forge pool-completion provisional score using current BLS/O*NET evidence and sampled Etsy competition. Lower confidence is intentional where exact employment sizing or clean marketplace decomposition is unavailable. Дата: 2026-09-23 10:04:52.652496+00.
- **repeatability**: 8.00 (confidence 0.580). Forge pool-completion provisional score using current BLS/O*NET evidence and sampled Etsy competition. Lower confidence is intentional where exact employment sizing or clean marketplace decomposition is unavailable. Дата: 2026-09-23 10:04:52.652496+00.
- **visual_language**: 9.50 (confidence 0.720). Forge pool-completion provisional score using current BLS/O*NET evidence and sampled Etsy competition. Lower confidence is intentional where exact employment sizing or clean marketplace decomposition is unavailable. Дата: 2026-09-23 10:04:52.652496+00.

### Концепции (0)

## 11. Cytotechnologist / Cytologist
Ключ: `cytotechnologist` · ID: `2be782f0-ba27-4ed5-a75d-6c2b26e8eaa2`

**Статус БД:** shortlisted · **балл:** 80.60 · **confidence:** 70.74 · **coverage:** 100.00
**Аудитория:** Cytotechnologists / cytologists in clinical pathology laboratories
**Категория:** occupational_identity
**Исследовательская аргументация:** Deep microscope/cell-pattern identity with authentic workflow around prepare, stain, examine, classify and document. Exact profession sizing is bundled into broader lab employment, so demand confidence is lower; marketplace is relatively small at 17+ sampled Etsy items.
**Создано / обновлено:** 2026-09-23 09:56:40.513406+00 / 2026-09-23 10:03:30.159451+00

### Компоненты оценки ниши

- **channel_breadth**: 7.50 (confidence 0.600). Forge diversity-batch v3 score using current 2025-35 BLS/O*NET evidence plus sampled current Etsy competition. Where exact marketplace counts were unavailable, competition confidence is intentionally lower. Дата: 2026-09-23 09:56:40.513406+00.
- **competition_opportunity**: 8.00 (confidence 0.820). Forge diversity-batch v3 score using current 2025-35 BLS/O*NET evidence plus sampled current Etsy competition. Where exact marketplace counts were unavailable, competition confidence is intentionally lower. Дата: 2026-09-23 09:56:40.513406+00.
- **concept_depth**: 9.50 (confidence 0.820). Forge diversity-batch v3 score using current 2025-35 BLS/O*NET evidence plus sampled current Etsy competition. Where exact marketplace counts were unavailable, competition confidence is intentionally lower. Дата: 2026-09-23 09:56:40.513406+00.
- **demand_evidence**: 6.50 (confidence 0.520). Forge diversity-batch v3 score using current 2025-35 BLS/O*NET evidence plus sampled current Etsy competition. Where exact marketplace counts were unavailable, competition confidence is intentionally lower. Дата: 2026-09-23 09:56:40.513406+00.
- **founder_edge**: 2.00 (confidence 0.400). Forge diversity-batch v3 score using current 2025-35 BLS/O*NET evidence plus sampled current Etsy competition. Where exact marketplace counts were unavailable, competition confidence is intentionally lower. Дата: 2026-09-23 09:56:40.513406+00.
- **identity_intensity**: 9.00 (confidence 0.780). Forge diversity-batch v3 score using current 2025-35 BLS/O*NET evidence plus sampled current Etsy competition. Where exact marketplace counts were unavailable, competition confidence is intentionally lower. Дата: 2026-09-23 09:56:40.513406+00.
- **legal_safety**: 8.50 (confidence 0.640). Forge diversity-batch v3 score using current 2025-35 BLS/O*NET evidence plus sampled current Etsy competition. Where exact marketplace counts were unavailable, competition confidence is intentionally lower. Дата: 2026-09-23 09:56:40.513406+00.
- **purchase_motivation**: 8.00 (confidence 0.700). Forge diversity-batch v3 score using current 2025-35 BLS/O*NET evidence plus sampled current Etsy competition. Where exact marketplace counts were unavailable, competition confidence is intentionally lower. Дата: 2026-09-23 09:56:40.513406+00.
- **repeatability**: 8.00 (confidence 0.680). Forge diversity-batch v3 score using current 2025-35 BLS/O*NET evidence plus sampled current Etsy competition. Where exact marketplace counts were unavailable, competition confidence is intentionally lower. Дата: 2026-09-23 09:56:40.513406+00.
- **visual_language**: 10.00 (confidence 0.860). Forge diversity-batch v3 score using current 2025-35 BLS/O*NET evidence plus sampled current Etsy competition. Where exact marketplace counts were unavailable, competition confidence is intentionally lower. Дата: 2026-09-23 09:56:40.513406+00.

### Концепции (17)

#### Cytology — cell / nucleus / morphology / pattern
`cyto_cell_nucleus_morphology_pattern` · ID `7d30a222-3c96-4635-b98f-868ee862f04a`

**Интерпретация:** Исторический: снят после owner review; не возвращать автоматически
**Статус БД:** scored · **балл:** 89.56 · **confidence:** 71.92 · **coverage:** 100.00
**Текст / хук:** CELL • NUCLEUS • MORPHOLOGY • PATTERN
**Идея:** CELL • NUCLEUS • MORPHOLOGY • PATTERN with an original microscopic cell-pattern field emphasizing morphology recognition, not a diagnostic claim.
**Покупатель:** Cytotechnologists and cytologists
**Причина покупки:** Deep professional vocabulary and strong visual language.
**Отличие:** Distinctive morphology/pattern framing rather than cute lab art.
**Визуальное направление:** Original microscopic pattern field.
**retired_reason:** failed purchase-trigger quality bar after owner review
**Создано / обновлено:** 2026-09-23 09:59:11.838032+00 / 2026-09-23 23:40:31.847823+00

Компоненты оценки:
- **buyer_desire**: 8.43 (confidence 0.717). Unified Forge diversity-v3 concept score grounded in current occupational tasks and niche evidence. No visual generated; phrase/IP review remains separate. Дата: 2026-09-23 09:59:11.838032+00.
- **clarity_at_glance**: 7.90 (confidence 0.687). Unified Forge diversity-v3 concept score grounded in current occupational tasks and niche evidence. No visual generated; phrase/IP review remains separate. Дата: 2026-09-23 09:59:11.838032+00.
- **distinctiveness**: 9.40 (confidence 0.732). Unified Forge diversity-v3 concept score grounded in current occupational tasks and niche evidence. No visual generated; phrase/IP review remains separate. Дата: 2026-09-23 09:59:11.838032+00.
- **giftability**: 7.43 (confidence 0.672). Unified Forge diversity-v3 concept score grounded in current occupational tasks and niche evidence. No visual generated; phrase/IP review remains separate. Дата: 2026-09-23 09:59:11.838032+00.
- **insider_resonance**: 9.40 (confidence 0.747). Unified Forge diversity-v3 concept score grounded in current occupational tasks and niche evidence. No visual generated; phrase/IP review remains separate. Дата: 2026-09-23 09:59:11.838032+00.
- **ip_safety**: 8.90 (confidence 0.550). Unified Forge diversity-v3 concept score grounded in current occupational tasks and niche evidence. No visual generated; phrase/IP review remains separate. Дата: 2026-09-23 09:59:11.838032+00.
- **niche_fit**: 9.63 (confidence 0.747). Unified Forge diversity-v3 concept score grounded in current occupational tasks and niche evidence. No visual generated; phrase/IP review remains separate. Дата: 2026-09-23 09:59:11.838032+00.
- **visual_potential**: 9.80 (confidence 0.762). Unified Forge diversity-v3 concept score grounded in current occupational tasks and niche evidence. No visual generated; phrase/IP review remains separate. Дата: 2026-09-23 09:59:11.838032+00.

#### Cytology — cell pattern analysis
`cyto_cell_nucleus_pattern_abnormality` · ID `35b72331-048d-49e8-98f5-a4ed6583998f`

**Интерпретация:** Исторический: семантический дубликат
**Статус БД:** paused · **балл:** 88.80 · **confidence:** 68.17 · **coverage:** 100.00
**Текст / хук:** CELL • NUCLEUS • PATTERN • ABNORMALITY
**Идея:** Cytology — cell pattern analysis. Core hook: CELL • NUCLEUS • PATTERN • ABNORMALITY. Grounded in current occupational tasks and intended as insider identity art, not operating/medical instruction. Avoid employer, OEM, certification-body and proprietary-interface branding.
**Покупатель:** Cytotechnologists / cytologists
**Причина покупки:** Professional identity purchase for cytotechnologists / cytologists who recognize the real tools, measurements and workflow.
**Отличие:** Technical technical map direction designed to avoid generic job-title, floral, retro-badge and parody templates.
**Визуальное направление:** Microscopy identity based on cell morphology and pattern recognition; stylized original cellular forms.
**semantic_duplicate_of:** cyto_cell_nucleus_morphology_pattern
**semantic_duplicate_reason:** Same core cell/nucleus/pattern morphology-analysis concept; existing concept is stronger and cleaner.
**Создано / обновлено:** 2026-09-23 10:02:18.463532+00 / 2026-09-23 10:05:50.016716+00

Компоненты оценки:
- **buyer_desire**: 8.47 (confidence 0.670). Provisional Forge challenger-concept score derived from occupationally grounded concept archetype plus the fully scored niche prior. It is a research-priority score, not a sales forecast or legal clearance. Дата: 2026-09-23 10:02:33.245254+00.
- **clarity_at_glance**: 7.80 (confidence 0.670). Provisional Forge challenger-concept score derived from occupationally grounded concept archetype plus the fully scored niche prior. It is a research-priority score, not a sales forecast or legal clearance. Дата: 2026-09-23 10:02:33.245254+00.
- **distinctiveness**: 9.30 (confidence 0.670). Provisional Forge challenger-concept score derived from occupationally grounded concept archetype plus the fully scored niche prior. It is a research-priority score, not a sales forecast or legal clearance. Дата: 2026-09-23 10:02:33.245254+00.
- **giftability**: 7.50 (confidence 0.670). Provisional Forge challenger-concept score derived from occupationally grounded concept archetype plus the fully scored niche prior. It is a research-priority score, not a sales forecast or legal clearance. Дата: 2026-09-23 10:02:33.245254+00.
- **insider_resonance**: 9.35 (confidence 0.700). Provisional Forge challenger-concept score derived from occupationally grounded concept archetype plus the fully scored niche prior. It is a research-priority score, not a sales forecast or legal clearance. Дата: 2026-09-23 10:02:33.245254+00.
- **ip_safety**: 8.60 (confidence 0.670). Provisional Forge challenger-concept score derived from occupationally grounded concept archetype plus the fully scored niche prior. It is a research-priority score, not a sales forecast or legal clearance. Дата: 2026-09-23 10:02:33.245254+00.
- **niche_fit**: 9.35 (confidence 0.700). Provisional Forge challenger-concept score derived from occupationally grounded concept archetype plus the fully scored niche prior. It is a research-priority score, not a sales forecast or legal clearance. Дата: 2026-09-23 10:02:33.245254+00.
- **visual_potential**: 9.65 (confidence 0.700). Provisional Forge challenger-concept score derived from occupationally grounded concept archetype plus the fully scored niche prior. It is a research-priority score, not a sales forecast or legal clearance. Дата: 2026-09-23 10:02:33.245254+00.

#### Cytology — PAP / FNA / body fluids
`cyto_pap_fna_body_fluids` · ID `70a3784e-c04d-4c2e-9090-e4ce940ae662`

**Интерпретация:** Исследовательский кандидат; одобрение владельца не зафиксировано
**Статус БД:** scored · **балл:** 87.92 · **confidence:** 70.80 · **coverage:** 100.00
**Текст / хук:** PAP • FNA • BODY FLUIDS
**Идея:** PAP • FNA • BODY FLUIDS as descriptive specimen categories grounded in O*NET tasks, supported by generic slide/sample forms.
**Покупатель:** Cytotechnologists and cytologists
**Причина покупки:** Immediate insider recognition across common cytology specimen types.
**Отличие:** Specialty terminology rather than generic pathology merch.
**Визуальное направление:** Technical specimen-category layout.
**Создано / обновлено:** 2026-09-23 09:59:11.838032+00 / 2026-09-23 10:05:50.016716+00

Компоненты оценки:
- **buyer_desire**: 8.73 (confidence 0.717). Unified Forge diversity-v3 concept score grounded in current occupational tasks and niche evidence. No visual generated; phrase/IP review remains separate. Дата: 2026-09-23 09:59:11.838032+00.
- **clarity_at_glance**: 9.30 (confidence 0.747). Unified Forge diversity-v3 concept score grounded in current occupational tasks and niche evidence. No visual generated; phrase/IP review remains separate. Дата: 2026-09-23 09:59:11.838032+00.
- **distinctiveness**: 8.40 (confidence 0.687). Unified Forge diversity-v3 concept score grounded in current occupational tasks and niche evidence. No visual generated; phrase/IP review remains separate. Дата: 2026-09-23 09:59:11.838032+00.
- **giftability**: 8.63 (confidence 0.709). Unified Forge diversity-v3 concept score grounded in current occupational tasks and niche evidence. No visual generated; phrase/IP review remains separate. Дата: 2026-09-23 09:59:11.838032+00.
- **insider_resonance**: 9.50 (confidence 0.762). Unified Forge diversity-v3 concept score grounded in current occupational tasks and niche evidence. No visual generated; phrase/IP review remains separate. Дата: 2026-09-23 09:59:11.838032+00.
- **ip_safety**: 8.00 (confidence 0.500). Unified Forge diversity-v3 concept score grounded in current occupational tasks and niche evidence. No visual generated; phrase/IP review remains separate. Дата: 2026-09-23 09:59:11.838032+00.
- **niche_fit**: 9.73 (confidence 0.769). Unified Forge diversity-v3 concept score grounded in current occupational tasks and niche evidence. No visual generated; phrase/IP review remains separate. Дата: 2026-09-23 09:59:11.838032+00.
- **visual_potential**: 8.10 (confidence 0.672). Unified Forge diversity-v3 concept score grounded in current occupational tasks and niche evidence. No visual generated; phrase/IP review remains separate. Дата: 2026-09-23 09:59:11.838032+00.

#### Cytology — specimen types
`cyto_pap_fna_fluid_slide` · ID `70ec5dc6-d6de-4bdc-bc81-e72d383696e0`

**Интерпретация:** Исторический: семантический дубликат
**Статус БД:** paused · **балл:** 87.02 · **confidence:** 67.17 · **coverage:** 100.00
**Текст / хук:** PAP • FNA • FLUID • SLIDE
**Идея:** Cytology — specimen types. Core hook: PAP • FNA • FLUID • SLIDE. Grounded in current occupational tasks and intended as insider identity art, not operating/medical instruction. Avoid employer, OEM, certification-body and proprietary-interface branding.
**Покупатель:** Cytotechnologists / cytologists
**Причина покупки:** Professional identity purchase for cytotechnologists / cytologists who recognize the real tools, measurements and workflow.
**Отличие:** Technical terminology direction designed to avoid generic job-title, floral, retro-badge and parody templates.
**Визуальное направление:** Specialty vocabulary grid using descriptive specimen categories and microscopy cues.
**semantic_duplicate_of:** cyto_pap_fna_body_fluids
**semantic_duplicate_reason:** Same PAP/FNA/body-fluid specimen-family hook; challenger only adds generic SLIDE.
**Создано / обновлено:** 2026-09-23 10:02:18.463532+00 / 2026-09-23 10:05:50.016716+00

Компоненты оценки:
- **buyer_desire**: 8.07 (confidence 0.660). Provisional Forge challenger-concept score derived from occupationally grounded concept archetype plus the fully scored niche prior. It is a research-priority score, not a sales forecast or legal clearance. Дата: 2026-09-23 10:02:33.245254+00.
- **clarity_at_glance**: 9.27 (confidence 0.660). Provisional Forge challenger-concept score derived from occupationally grounded concept archetype plus the fully scored niche prior. It is a research-priority score, not a sales forecast or legal clearance. Дата: 2026-09-23 10:02:33.245254+00.
- **distinctiveness**: 8.50 (confidence 0.660). Provisional Forge challenger-concept score derived from occupationally grounded concept archetype plus the fully scored niche prior. It is a research-priority score, not a sales forecast or legal clearance. Дата: 2026-09-23 10:02:33.245254+00.
- **giftability**: 8.17 (confidence 0.660). Provisional Forge challenger-concept score derived from occupationally grounded concept archetype plus the fully scored niche prior. It is a research-priority score, not a sales forecast or legal clearance. Дата: 2026-09-23 10:02:33.245254+00.
- **insider_resonance**: 9.50 (confidence 0.690). Provisional Forge challenger-concept score derived from occupationally grounded concept archetype plus the fully scored niche prior. It is a research-priority score, not a sales forecast or legal clearance. Дата: 2026-09-23 10:02:33.245254+00.
- **ip_safety**: 8.80 (confidence 0.660). Provisional Forge challenger-concept score derived from occupationally grounded concept archetype plus the fully scored niche prior. It is a research-priority score, not a sales forecast or legal clearance. Дата: 2026-09-23 10:02:33.245254+00.
- **niche_fit**: 9.45 (confidence 0.690). Provisional Forge challenger-concept score derived from occupationally grounded concept archetype plus the fully scored niche prior. It is a research-priority score, not a sales forecast or legal clearance. Дата: 2026-09-23 10:02:33.245254+00.
- **visual_potential**: 8.50 (confidence 0.690). Provisional Forge challenger-concept score derived from occupationally grounded concept archetype plus the fully scored niche prior. It is a research-priority score, not a sales forecast or legal clearance. Дата: 2026-09-23 10:02:33.245254+00.

#### Cytology — prep / stain / screen / report
`cyto_prep_stain_screen_report` · ID `3ac347c1-e171-4701-b6e1-1ab7eb5a8603`

**Интерпретация:** Исторический: семантический дубликат
**Статус БД:** paused · **балл:** 86.29 · **confidence:** 67.17 · **coverage:** 100.00
**Текст / хук:** PREP → STAIN → SCREEN → REPORT
**Идея:** Cytology — prep / stain / screen / report. Core hook: PREP → STAIN → SCREEN → REPORT. Grounded in current occupational tasks and intended as insider identity art, not operating/medical instruction. Avoid employer, OEM, certification-body and proprietary-interface branding.
**Покупатель:** Cytotechnologists / cytologists
**Причина покупки:** Professional identity purchase for cytotechnologists / cytologists who recognize the real tools, measurements and workflow.
**Отличие:** Technical workflow direction designed to avoid generic job-title, floral, retro-badge and parody templates.
**Визуальное направление:** Cytology workflow with slide, stain and microscope motifs; no lab/company branding.
**semantic_duplicate_of:** cyto_stain_screen_identify_report
**semantic_duplicate_reason:** Same cytology preparation/stain/screen/report workflow; existing concept is stronger and adds identification.
**Создано / обновлено:** 2026-09-23 10:02:18.463532+00 / 2026-09-23 10:05:50.016716+00

Компоненты оценки:
- **buyer_desire**: 8.37 (confidence 0.660). Provisional Forge challenger-concept score derived from occupationally grounded concept archetype plus the fully scored niche prior. It is a research-priority score, not a sales forecast or legal clearance. Дата: 2026-09-23 10:02:33.245254+00.
- **clarity_at_glance**: 9.20 (confidence 0.660). Provisional Forge challenger-concept score derived from occupationally grounded concept archetype plus the fully scored niche prior. It is a research-priority score, not a sales forecast or legal clearance. Дата: 2026-09-23 10:02:33.245254+00.
- **distinctiveness**: 8.50 (confidence 0.660). Provisional Forge challenger-concept score derived from occupationally grounded concept archetype plus the fully scored niche prior. It is a research-priority score, not a sales forecast or legal clearance. Дата: 2026-09-23 10:02:33.245254+00.
- **giftability**: 8.10 (confidence 0.660). Provisional Forge challenger-concept score derived from occupationally grounded concept archetype plus the fully scored niche prior. It is a research-priority score, not a sales forecast or legal clearance. Дата: 2026-09-23 10:02:33.245254+00.
- **insider_resonance**: 8.85 (confidence 0.690). Provisional Forge challenger-concept score derived from occupationally grounded concept archetype plus the fully scored niche prior. It is a research-priority score, not a sales forecast or legal clearance. Дата: 2026-09-23 10:02:33.245254+00.
- **ip_safety**: 9.00 (confidence 0.660). Provisional Forge challenger-concept score derived from occupationally grounded concept archetype plus the fully scored niche prior. It is a research-priority score, not a sales forecast or legal clearance. Дата: 2026-09-23 10:02:33.245254+00.
- **niche_fit**: 9.25 (confidence 0.690). Provisional Forge challenger-concept score derived from occupationally grounded concept archetype plus the fully scored niche prior. It is a research-priority score, not a sales forecast or legal clearance. Дата: 2026-09-23 10:02:33.245254+00.
- **visual_potential**: 8.45 (confidence 0.690). Provisional Forge challenger-concept score derived from occupationally grounded concept archetype plus the fully scored niche prior. It is a research-priority score, not a sales forecast or legal clearance. Дата: 2026-09-23 10:02:33.245254+00.

#### Cytology — prepare / stain / examine / document
`cyto_prepare_stain_examine_document` · ID `23d67f21-9b6b-4c36-a7cb-bd9e6d285e77`

**Интерпретация:** Исследовательский кандидат; одобрение владельца не зафиксировано
**Статус БД:** scored · **балл:** 88.39 · **confidence:** 71.80 · **coverage:** 100.00
**Текст / хук:** PREPARE • STAIN • EXAMINE • DOCUMENT
**Идея:** PREPARE • STAIN • EXAMINE • DOCUMENT as a four-step laboratory identity grounded in specimen preparation, staining, microscopy and documentation.
**Покупатель:** Cytotechnologists and cytologists
**Причина покупки:** Clear full-cycle cytology workflow.
**Отличие:** Profession-specific process language with strong series potential.
**Визуальное направление:** Four-step laboratory process composition.
**Создано / обновлено:** 2026-09-23 09:59:11.838032+00 / 2026-09-23 09:59:11.838032+00

Компоненты оценки:
- **buyer_desire**: 8.43 (confidence 0.717). Unified Forge diversity-v3 concept score grounded in current occupational tasks and niche evidence. No visual generated; phrase/IP review remains separate. Дата: 2026-09-23 09:59:11.838032+00.
- **clarity_at_glance**: 8.40 (confidence 0.709). Unified Forge diversity-v3 concept score grounded in current occupational tasks and niche evidence. No visual generated; phrase/IP review remains separate. Дата: 2026-09-23 09:59:11.838032+00.
- **distinctiveness**: 9.00 (confidence 0.724). Unified Forge diversity-v3 concept score grounded in current occupational tasks and niche evidence. No visual generated; phrase/IP review remains separate. Дата: 2026-09-23 09:59:11.838032+00.
- **giftability**: 7.83 (confidence 0.679). Unified Forge diversity-v3 concept score grounded in current occupational tasks and niche evidence. No visual generated; phrase/IP review remains separate. Дата: 2026-09-23 09:59:11.838032+00.
- **insider_resonance**: 9.10 (confidence 0.739). Unified Forge diversity-v3 concept score grounded in current occupational tasks and niche evidence. No visual generated; phrase/IP review remains separate. Дата: 2026-09-23 09:59:11.838032+00.
- **ip_safety**: 8.90 (confidence 0.550). Unified Forge diversity-v3 concept score grounded in current occupational tasks and niche evidence. No visual generated; phrase/IP review remains separate. Дата: 2026-09-23 09:59:11.838032+00.
- **niche_fit**: 9.53 (confidence 0.754). Unified Forge diversity-v3 concept score grounded in current occupational tasks and niche evidence. No visual generated; phrase/IP review remains separate. Дата: 2026-09-23 09:59:11.838032+00.
- **visual_potential**: 9.40 (confidence 0.754). Unified Forge diversity-v3 concept score grounded in current occupational tasks and niche evidence. No visual generated; phrase/IP review remains separate. Дата: 2026-09-23 09:59:11.838032+00.

#### Cytology — screen / flag / pathologist
`cyto_screen_flag_pathologist` · ID `4b7b1c79-aee7-4fb7-9ff3-ddeea3c39b22`

**Интерпретация:** Исследовательский кандидат; одобрение владельца не зафиксировано
**Статус БД:** scored · **балл:** 88.09 · **confidence:** 71.27 · **coverage:** 100.00
**Текст / хук:** SCREEN → FLAG → PATHOLOGIST
**Идея:** SCREEN → FLAG → PATHOLOGIST reflecting the O*NET task of submitting abnormal slides for pathologist examination, without diagnosis wording.
**Покупатель:** Cytotechnologists and cytologists
**Причина покупки:** Recognizable professional handoff workflow.
**Отличие:** Specific professional judgment/handoff rather than generic lab workflow.
**Визуальное направление:** Slide screening to review handoff diagram.
**Создано / обновлено:** 2026-09-23 09:59:11.838032+00 / 2026-09-23 09:59:11.838032+00

Компоненты оценки:
- **buyer_desire**: 8.63 (confidence 0.724). Unified Forge diversity-v3 concept score grounded in current occupational tasks and niche evidence. No visual generated; phrase/IP review remains separate. Дата: 2026-09-23 09:59:11.838032+00.
- **clarity_at_glance**: 9.40 (confidence 0.754). Unified Forge diversity-v3 concept score grounded in current occupational tasks and niche evidence. No visual generated; phrase/IP review remains separate. Дата: 2026-09-23 09:59:11.838032+00.
- **distinctiveness**: 8.70 (confidence 0.709). Unified Forge diversity-v3 concept score grounded in current occupational tasks and niche evidence. No visual generated; phrase/IP review remains separate. Дата: 2026-09-23 09:59:11.838032+00.
- **giftability**: 8.43 (confidence 0.702). Unified Forge diversity-v3 concept score grounded in current occupational tasks and niche evidence. No visual generated; phrase/IP review remains separate. Дата: 2026-09-23 09:59:11.838032+00.
- **insider_resonance**: 9.00 (confidence 0.732). Unified Forge diversity-v3 concept score grounded in current occupational tasks and niche evidence. No visual generated; phrase/IP review remains separate. Дата: 2026-09-23 09:59:11.838032+00.
- **ip_safety**: 9.10 (confidence 0.550). Unified Forge diversity-v3 concept score grounded in current occupational tasks and niche evidence. No visual generated; phrase/IP review remains separate. Дата: 2026-09-23 09:59:11.838032+00.
- **niche_fit**: 9.33 (confidence 0.739). Unified Forge diversity-v3 concept score grounded in current occupational tasks and niche evidence. No visual generated; phrase/IP review remains separate. Дата: 2026-09-23 09:59:11.838032+00.
- **visual_potential**: 8.50 (confidence 0.702). Unified Forge diversity-v3 concept score grounded in current occupational tasks and niche evidence. No visual generated; phrase/IP review remains separate. Дата: 2026-09-23 09:59:11.838032+00.

#### Cytology — slide to pathologist
`cyto_slide_microscope_review_pathologist` · ID `78b41da8-ca5f-43de-9964-be0c6434136e`

**Интерпретация:** Исследовательский кандидат; одобрение владельца не зафиксировано
**Статус БД:** scored · **балл:** 88.19 · **confidence:** 69.17 · **coverage:** 100.00
**Текст / хук:** SLIDE → MICROSCOPE → REVIEW → PATHOLOGIST
**Идея:** Cytology — slide to pathologist. Core hook: SLIDE → MICROSCOPE → REVIEW → PATHOLOGIST. Grounded in current occupational tasks and intended as insider identity art, not operating/medical instruction. Avoid employer, OEM, certification-body and proprietary-interface branding.
**Покупатель:** Cytotechnologists / cytologists
**Причина покупки:** Professional identity purchase for cytotechnologists / cytologists who recognize the real tools, measurements and workflow.
**Отличие:** Technical system map direction designed to avoid generic job-title, floral, retro-badge and parody templates.
**Визуальное направление:** Professional interpretation path from prepared slide through microscopic review to escalation/reporting.
**Создано / обновлено:** 2026-09-23 10:02:18.463532+00 / 2026-09-23 10:04:16.501026+00

Компоненты оценки:
- **buyer_desire**: 8.47 (confidence 0.680). Provisional Forge challenger-concept score derived from occupationally grounded concept archetype plus the fully scored niche prior. It is a research-priority score, not a sales forecast or legal clearance. Дата: 2026-09-23 10:02:33.245254+00.
- **clarity_at_glance**: 8.17 (confidence 0.680). Provisional Forge challenger-concept score derived from occupationally grounded concept archetype plus the fully scored niche prior. It is a research-priority score, not a sales forecast or legal clearance. Дата: 2026-09-23 10:02:33.245254+00.
- **distinctiveness**: 9.00 (confidence 0.680). Provisional Forge challenger-concept score derived from occupationally grounded concept archetype plus the fully scored niche prior. It is a research-priority score, not a sales forecast or legal clearance. Дата: 2026-09-23 10:02:33.245254+00.
- **giftability**: 7.57 (confidence 0.680). Provisional Forge challenger-concept score derived from occupationally grounded concept archetype plus the fully scored niche prior. It is a research-priority score, not a sales forecast or legal clearance. Дата: 2026-09-23 10:02:33.245254+00.
- **insider_resonance**: 9.10 (confidence 0.710). Provisional Forge challenger-concept score derived from occupationally grounded concept archetype plus the fully scored niche prior. It is a research-priority score, not a sales forecast or legal clearance. Дата: 2026-09-23 10:02:33.245254+00.
- **ip_safety**: 8.80 (confidence 0.680). Provisional Forge challenger-concept score derived from occupationally grounded concept archetype plus the fully scored niche prior. It is a research-priority score, not a sales forecast or legal clearance. Дата: 2026-09-23 10:02:33.245254+00.
- **niche_fit**: 9.35 (confidence 0.710). Provisional Forge challenger-concept score derived from occupationally grounded concept archetype plus the fully scored niche prior. It is a research-priority score, not a sales forecast or legal clearance. Дата: 2026-09-23 10:02:33.245254+00.
- **visual_potential**: 9.60 (confidence 0.710). Provisional Forge challenger-concept score derived from occupationally grounded concept archetype plus the fully scored niche prior. It is a research-priority score, not a sales forecast or legal clearance. Дата: 2026-09-23 10:02:33.245254+00.

#### Cytology — quality / morphology / documentation
`cyto_specimen_quality_morphology_document` · ID `93f0c5e0-aa76-44ae-98a5-52e6cfe5d6d1`

**Интерпретация:** Исследовательский кандидат; одобрение владельца не зафиксировано
**Статус БД:** scored · **балл:** 87.02 · **confidence:** 67.17 · **coverage:** 100.00
**Текст / хук:** SPECIMEN • QUALITY • MORPHOLOGY • DOCUMENT
**Идея:** Cytology — quality / morphology / documentation. Core hook: SPECIMEN • QUALITY • MORPHOLOGY • DOCUMENT. Grounded in current occupational tasks and intended as insider identity art, not operating/medical instruction. Avoid employer, OEM, certification-body and proprietary-interface branding.
**Покупатель:** Cytotechnologists / cytologists
**Причина покупки:** Professional identity purchase for cytotechnologists / cytologists who recognize the real tools, measurements and workflow.
**Отличие:** Technical terminology direction designed to avoid generic job-title, floral, retro-badge and parody templates.
**Визуальное направление:** Four-part technical identity emphasizing specimen quality, morphology and documentation.
**Создано / обновлено:** 2026-09-23 10:02:18.463532+00 / 2026-09-23 10:02:33.245254+00

Компоненты оценки:
- **buyer_desire**: 8.07 (confidence 0.660). Provisional Forge challenger-concept score derived from occupationally grounded concept archetype plus the fully scored niche prior. It is a research-priority score, not a sales forecast or legal clearance. Дата: 2026-09-23 10:02:33.245254+00.
- **clarity_at_glance**: 9.27 (confidence 0.660). Provisional Forge challenger-concept score derived from occupationally grounded concept archetype plus the fully scored niche prior. It is a research-priority score, not a sales forecast or legal clearance. Дата: 2026-09-23 10:02:33.245254+00.
- **distinctiveness**: 8.50 (confidence 0.660). Provisional Forge challenger-concept score derived from occupationally grounded concept archetype plus the fully scored niche prior. It is a research-priority score, not a sales forecast or legal clearance. Дата: 2026-09-23 10:02:33.245254+00.
- **giftability**: 8.17 (confidence 0.660). Provisional Forge challenger-concept score derived from occupationally grounded concept archetype plus the fully scored niche prior. It is a research-priority score, not a sales forecast or legal clearance. Дата: 2026-09-23 10:02:33.245254+00.
- **insider_resonance**: 9.50 (confidence 0.690). Provisional Forge challenger-concept score derived from occupationally grounded concept archetype plus the fully scored niche prior. It is a research-priority score, not a sales forecast or legal clearance. Дата: 2026-09-23 10:02:33.245254+00.
- **ip_safety**: 8.80 (confidence 0.660). Provisional Forge challenger-concept score derived from occupationally grounded concept archetype plus the fully scored niche prior. It is a research-priority score, not a sales forecast or legal clearance. Дата: 2026-09-23 10:02:33.245254+00.
- **niche_fit**: 9.45 (confidence 0.690). Provisional Forge challenger-concept score derived from occupationally grounded concept archetype plus the fully scored niche prior. It is a research-priority score, not a sales forecast or legal clearance. Дата: 2026-09-23 10:02:33.245254+00.
- **visual_potential**: 8.50 (confidence 0.690). Provisional Forge challenger-concept score derived from occupationally grounded concept archetype plus the fully scored niche prior. It is a research-priority score, not a sales forecast or legal clearance. Дата: 2026-09-23 10:02:33.245254+00.

#### Cytology — specimen to microscope
`cyto_specimen_slide_microscope` · ID `02de105f-d608-4ed7-84f6-a5c12e3f5de3`

**Интерпретация:** Исследовательский кандидат; одобрение владельца не зафиксировано
**Статус БД:** scored · **балл:** 89.22 · **confidence:** 72.12 · **coverage:** 100.00
**Текст / хук:** SPECIMEN → SLIDE → MICROSCOPE
**Идея:** SPECIMEN → SLIDE → MICROSCOPE as a three-stage cytology chain with original line art.
**Покупатель:** Cytotechnologists and cytologists
**Причина покупки:** Simple, readable profession-specific process identity.
**Отличие:** More specific than generic microscope or science graphics.
**Визуальное направление:** Three-stage specimen/slide/microscope map.
**Создано / обновлено:** 2026-09-23 09:59:11.838032+00 / 2026-09-23 10:04:16.501026+00

Компоненты оценки:
- **buyer_desire**: 8.53 (confidence 0.717). Unified Forge diversity-v3 concept score grounded in current occupational tasks and niche evidence. No visual generated; phrase/IP review remains separate. Дата: 2026-09-23 09:59:11.838032+00.
- **clarity_at_glance**: 8.00 (confidence 0.694). Unified Forge diversity-v3 concept score grounded in current occupational tasks and niche evidence. No visual generated; phrase/IP review remains separate. Дата: 2026-09-23 09:59:11.838032+00.
- **distinctiveness**: 9.20 (confidence 0.732). Unified Forge diversity-v3 concept score grounded in current occupational tasks and niche evidence. No visual generated; phrase/IP review remains separate. Дата: 2026-09-23 09:59:11.838032+00.
- **giftability**: 7.53 (confidence 0.672). Unified Forge diversity-v3 concept score grounded in current occupational tasks and niche evidence. No visual generated; phrase/IP review remains separate. Дата: 2026-09-23 09:59:11.838032+00.
- **insider_resonance**: 9.20 (confidence 0.747). Unified Forge diversity-v3 concept score grounded in current occupational tasks and niche evidence. No visual generated; phrase/IP review remains separate. Дата: 2026-09-23 09:59:11.838032+00.
- **ip_safety**: 8.90 (confidence 0.550). Unified Forge diversity-v3 concept score grounded in current occupational tasks and niche evidence. No visual generated; phrase/IP review remains separate. Дата: 2026-09-23 09:59:11.838032+00.
- **niche_fit**: 9.63 (confidence 0.754). Unified Forge diversity-v3 concept score grounded in current occupational tasks and niche evidence. No visual generated; phrase/IP review remains separate. Дата: 2026-09-23 09:59:11.838032+00.
- **visual_potential**: 9.80 (confidence 0.769). Unified Forge diversity-v3 concept score grounded in current occupational tasks and niche evidence. No visual generated; phrase/IP review remains separate. Дата: 2026-09-23 09:59:11.838032+00.

#### Cytology — stain / mount / examine / classify
`cyto_stain_mount_examine_classify` · ID `5187acbb-8a03-47f3-b8ef-047709a28e24`

**Интерпретация:** Исследовательский кандидат; одобрение владельца не зафиксировано
**Статус БД:** scored · **балл:** 85.68 · **confidence:** 67.17 · **coverage:** 100.00
**Текст / хук:** STAIN • MOUNT • EXAMINE • CLASSIFY
**Идея:** Cytology — stain / mount / examine / classify. Core hook: STAIN • MOUNT • EXAMINE • CLASSIFY. Grounded in current occupational tasks and intended as insider identity art, not operating/medical instruction. Avoid employer, OEM, certification-body and proprietary-interface branding.
**Покупатель:** Cytotechnologists / cytologists
**Причина покупки:** Professional identity purchase for cytotechnologists / cytologists who recognize the real tools, measurements and workflow.
**Отличие:** Technical workflow direction designed to avoid generic job-title, floral, retro-badge and parody templates.
**Визуальное направление:** Laboratory workflow concept grounded in O*NET cytotechnologist tasks.
**Создано / обновлено:** 2026-09-23 10:02:18.463532+00 / 2026-09-23 10:02:33.245254+00

Компоненты оценки:
- **buyer_desire**: 8.27 (confidence 0.660). Provisional Forge challenger-concept score derived from occupationally grounded concept archetype plus the fully scored niche prior. It is a research-priority score, not a sales forecast or legal clearance. Дата: 2026-09-23 10:02:33.245254+00.
- **clarity_at_glance**: 9.17 (confidence 0.660). Provisional Forge challenger-concept score derived from occupationally grounded concept archetype plus the fully scored niche prior. It is a research-priority score, not a sales forecast or legal clearance. Дата: 2026-09-23 10:02:33.245254+00.
- **distinctiveness**: 8.40 (confidence 0.660). Provisional Forge challenger-concept score derived from occupationally grounded concept archetype plus the fully scored niche prior. It is a research-priority score, not a sales forecast or legal clearance. Дата: 2026-09-23 10:02:33.245254+00.
- **giftability**: 8.07 (confidence 0.660). Provisional Forge challenger-concept score derived from occupationally grounded concept archetype plus the fully scored niche prior. It is a research-priority score, not a sales forecast or legal clearance. Дата: 2026-09-23 10:02:33.245254+00.
- **insider_resonance**: 8.80 (confidence 0.690). Provisional Forge challenger-concept score derived from occupationally grounded concept archetype plus the fully scored niche prior. It is a research-priority score, not a sales forecast or legal clearance. Дата: 2026-09-23 10:02:33.245254+00.
- **ip_safety**: 9.00 (confidence 0.660). Provisional Forge challenger-concept score derived from occupationally grounded concept archetype plus the fully scored niche prior. It is a research-priority score, not a sales forecast or legal clearance. Дата: 2026-09-23 10:02:33.245254+00.
- **niche_fit**: 9.25 (confidence 0.690). Provisional Forge challenger-concept score derived from occupationally grounded concept archetype plus the fully scored niche prior. It is a research-priority score, not a sales forecast or legal clearance. Дата: 2026-09-23 10:02:33.245254+00.
- **visual_potential**: 8.40 (confidence 0.690). Provisional Forge challenger-concept score derived from occupationally grounded concept archetype plus the fully scored niche prior. It is a research-priority score, not a sales forecast or legal clearance. Дата: 2026-09-23 10:02:33.245254+00.

#### Cytology — stain / screen / identify / report
`cyto_stain_screen_identify_report` · ID `3dc79458-1446-4169-bc9a-77847f30526a`

**Интерпретация:** Исторический: снят после owner review; не возвращать автоматически
**Статус БД:** scored · **балл:** 89.39 · **confidence:** 71.80 · **coverage:** 100.00
**Текст / хук:** STAIN • SCREEN • IDENTIFY • REPORT
**Идея:** STAIN • SCREEN • IDENTIFY • REPORT using original cell/slide/microscope geometry and pathology-report cues.
**Покупатель:** Cytotechnologists and cytologists
**Причина покупки:** Strong insider laboratory workflow identity.
**Отличие:** Specific cytology process language rather than generic lab-tech merch.
**Визуальное направление:** Original cell/slide/microscope process composition.
**retired_reason:** failed purchase-trigger quality bar after owner review
**Создано / обновлено:** 2026-09-23 09:59:11.838032+00 / 2026-09-23 23:40:31.847823+00

Компоненты оценки:
- **buyer_desire**: 8.53 (confidence 0.717). Unified Forge diversity-v3 concept score grounded in current occupational tasks and niche evidence. No visual generated; phrase/IP review remains separate. Дата: 2026-09-23 09:59:11.838032+00.
- **clarity_at_glance**: 8.50 (confidence 0.709). Unified Forge diversity-v3 concept score grounded in current occupational tasks and niche evidence. No visual generated; phrase/IP review remains separate. Дата: 2026-09-23 09:59:11.838032+00.
- **distinctiveness**: 9.10 (confidence 0.724). Unified Forge diversity-v3 concept score grounded in current occupational tasks and niche evidence. No visual generated; phrase/IP review remains separate. Дата: 2026-09-23 09:59:11.838032+00.
- **giftability**: 7.93 (confidence 0.679). Unified Forge diversity-v3 concept score grounded in current occupational tasks and niche evidence. No visual generated; phrase/IP review remains separate. Дата: 2026-09-23 09:59:11.838032+00.
- **insider_resonance**: 9.20 (confidence 0.739). Unified Forge diversity-v3 concept score grounded in current occupational tasks and niche evidence. No visual generated; phrase/IP review remains separate. Дата: 2026-09-23 09:59:11.838032+00.
- **ip_safety**: 9.00 (confidence 0.550). Unified Forge diversity-v3 concept score grounded in current occupational tasks and niche evidence. No visual generated; phrase/IP review remains separate. Дата: 2026-09-23 09:59:11.838032+00.
- **niche_fit**: 9.63 (confidence 0.754). Unified Forge diversity-v3 concept score grounded in current occupational tasks and niche evidence. No visual generated; phrase/IP review remains separate. Дата: 2026-09-23 09:59:11.838032+00.
- **visual_potential**: 9.50 (confidence 0.754). Unified Forge diversity-v3 concept score grounded in current occupational tasks and niche evidence. No visual generated; phrase/IP review remains separate. Дата: 2026-09-23 09:59:11.838032+00.

#### Cytology — cells confess
`v4_cyto_confess` · ID `84a98e62-5e2f-4f4d-a9d0-f304467eb221`

**Интерпретация:** V4: редакционный финалист на выбор владельца, НЕ подтвержденное одобрение
**Статус БД:** shortlisted · **балл:** 90.22 · **confidence:** 70.32 · **coverage:** 100.00
**Текст / хук:** I STARE AT CELLS UNTIL ONE CONFESSES.
**Идея:** Turn microscopic interpretation into a detective interrogation metaphor.
**Покупатель:** Cytotechnologists / cytologists
**Причина покупки:** Strong visual metaphor, identity humor and giftability.
**Отличие:** The hook is detective behavior, not cell terminology.
**Визуальное направление:** Microscope spotlight/interrogation room with stylized generic cells.
**Смысл для владельца (источник, EN):** The line compares careful microscopic examination to a detective interrogation: stare long enough and one suspicious cell finally “confesses.”
**Почему это шутка (источник, EN):** It turns patient, detail-heavy diagnostic work into a noir detective scene. The professional pride is that the cytotech is the person who notices the one abnormal cell hiding among many normal ones.
**Создано / обновлено:** 2026-09-23 19:58:09.189566+00 / 2026-09-24 22:40:42.70901+00

Компоненты оценки:
- **buyer_desire**: 9.00 (confidence 0.700). purchase_trigger_v2 preliminary score; gate passed; trigger=visual_metaphor Дата: 2026-09-23 19:59:53.152527+00.
- **clarity_at_glance**: 8.90 (confidence 0.760). purchase_trigger_v2 preliminary score; gate passed; trigger=visual_metaphor Дата: 2026-09-23 19:59:53.152527+00.
- **distinctiveness**: 9.20 (confidence 0.700). purchase_trigger_v2 preliminary score; gate passed; trigger=visual_metaphor Дата: 2026-09-23 19:59:53.152527+00.
- **giftability**: 8.60 (confidence 0.670). purchase_trigger_v2 preliminary score; gate passed; trigger=visual_metaphor Дата: 2026-09-23 19:59:53.152527+00.
- **insider_resonance**: 8.90 (confidence 0.720). purchase_trigger_v2 preliminary score; gate passed; trigger=visual_metaphor Дата: 2026-09-23 19:59:53.152527+00.
- **ip_safety**: 8.90 (confidence 0.600). purchase_trigger_v2 preliminary score; gate passed; trigger=visual_metaphor Дата: 2026-09-23 19:59:53.152527+00.
- **niche_fit**: 9.00 (confidence 0.720). purchase_trigger_v2 preliminary score; gate passed; trigger=visual_metaphor Дата: 2026-09-23 19:59:53.152527+00.
- **visual_potential**: 9.50 (confidence 0.720). purchase_trigger_v2 preliminary score; gate passed; trigger=visual_metaphor Дата: 2026-09-23 19:59:53.152527+00.

#### Cytology — microscopic coworkers
`v4_cyto_coworkers_cells` · ID `19d1f999-556a-4dac-a43a-540c077260f2`

**Интерпретация:** Исследовательский кандидат; одобрение владельца не зафиксировано
**Статус БД:** scored · **балл:** 88.47 · **confidence:** 70.32 · **coverage:** 100.00
**Текст / хук:** MOST OF MY COWORKERS FIT ON A SLIDE.
**Идея:** Play on spending more time with slides/cells than with people.
**Покупатель:** Cytotechnologists / cytologists
**Причина покупки:** Warm lab humor with a clear visual and gifting use.
**Отличие:** The joke is social isolation through microscope work, not a list of specimens.
**Визуальное направление:** Office-team portrait replaced by friendly stylized cells on a slide.
**Создано / обновлено:** 2026-09-23 19:58:09.189566+00 / 2026-09-24 05:05:38.621539+00

Компоненты оценки:
- **buyer_desire**: 8.80 (confidence 0.700). purchase_trigger_v2 preliminary score; gate passed; trigger=work_life_humor Дата: 2026-09-23 19:59:53.152527+00.
- **clarity_at_glance**: 9.20 (confidence 0.760). purchase_trigger_v2 preliminary score; gate passed; trigger=work_life_humor Дата: 2026-09-23 19:59:53.152527+00.
- **distinctiveness**: 8.50 (confidence 0.700). purchase_trigger_v2 preliminary score; gate passed; trigger=work_life_humor Дата: 2026-09-23 19:59:53.152527+00.
- **giftability**: 8.90 (confidence 0.670). purchase_trigger_v2 preliminary score; gate passed; trigger=work_life_humor Дата: 2026-09-23 19:59:53.152527+00.
- **insider_resonance**: 9.00 (confidence 0.720). purchase_trigger_v2 preliminary score; gate passed; trigger=work_life_humor Дата: 2026-09-23 19:59:53.152527+00.
- **ip_safety**: 8.90 (confidence 0.600). purchase_trigger_v2 preliminary score; gate passed; trigger=work_life_humor Дата: 2026-09-23 19:59:53.152527+00.
- **niche_fit**: 9.10 (confidence 0.720). purchase_trigger_v2 preliminary score; gate passed; trigger=work_life_humor Дата: 2026-09-23 19:59:53.152527+00.
- **visual_potential**: 8.80 (confidence 0.720). purchase_trigger_v2 preliminary score; gate passed; trigger=work_life_humor Дата: 2026-09-23 19:59:53.152527+00.

#### Cytology — obscure profession club
`v4_cyto_nobody_knows` · ID `009d21b5-c6f6-4c7c-b6d7-e1a7bd0992fa`

**Интерпретация:** Исследовательский кандидат; одобрение владельца не зафиксировано
**Статус БД:** scored · **балл:** 89.37 · **confidence:** 70.32 · **coverage:** 100.00
**Текст / хук:** NOBODY KNOWS WHAT A CYTOTECH IS. WE KNOW.
**Идея:** Use the fact that even healthcare peers often do not know what a cytotech is.
**Покупатель:** Cytotechnologists / cytologists
**Причина покупки:** Hidden-tribe identity and solidarity; easy gift from/for coworkers.
**Отличие:** The joke is social obscurity, not a vocabulary lesson.
**Визуальное направление:** Secret-club badge made from a microscope field, not generic medical iconography.
**Создано / обновлено:** 2026-09-23 19:58:09.189566+00 / 2026-09-24 05:05:38.621539+00

Компоненты оценки:
- **buyer_desire**: 8.80 (confidence 0.700). purchase_trigger_v2 preliminary score; gate passed; trigger=hidden_tribe_identity Дата: 2026-09-23 19:59:53.152527+00.
- **clarity_at_glance**: 9.10 (confidence 0.760). purchase_trigger_v2 preliminary score; gate passed; trigger=hidden_tribe_identity Дата: 2026-09-23 19:59:53.152527+00.
- **distinctiveness**: 8.70 (confidence 0.700). purchase_trigger_v2 preliminary score; gate passed; trigger=hidden_tribe_identity Дата: 2026-09-23 19:59:53.152527+00.
- **giftability**: 8.90 (confidence 0.670). purchase_trigger_v2 preliminary score; gate passed; trigger=hidden_tribe_identity Дата: 2026-09-23 19:59:53.152527+00.
- **insider_resonance**: 9.40 (confidence 0.720). purchase_trigger_v2 preliminary score; gate passed; trigger=hidden_tribe_identity Дата: 2026-09-23 19:59:53.152527+00.
- **ip_safety**: 8.90 (confidence 0.600). purchase_trigger_v2 preliminary score; gate passed; trigger=hidden_tribe_identity Дата: 2026-09-23 19:59:53.152527+00.
- **niche_fit**: 9.50 (confidence 0.720). purchase_trigger_v2 preliminary score; gate passed; trigger=hidden_tribe_identity Дата: 2026-09-23 19:59:53.152527+00.
- **visual_potential**: 8.70 (confidence 0.720). purchase_trigger_v2 preliminary score; gate passed; trigger=hidden_tribe_identity Дата: 2026-09-23 19:59:53.152527+00.

#### Cytology — seeing what others miss
`v4_cyto_see_others_miss` · ID `0b9a443e-417f-4fc1-ae48-f0a03a479f97`

**Интерпретация:** V4: понижен редакционным отбором, сохранен в истории
**Статус БД:** scored · **балл:** 82.12 · **confidence:** 70.32 · **coverage:** 100.00
**Текст / хук:** I SEE WHAT OTHERS MISS.
**Идея:** Serious pride concept about trained pattern recognition.
**Покупатель:** Cytotechnologists / cytologists
**Причина покупки:** Status/identity without overclaiming diagnosis or using generic job-title merch.
**Отличие:** Human skill first; technical context comes from visual language.
**Визуальное направление:** Microscope field with subtle anomaly illuminated; no medical claim text.
**editorial_reason:** generic inspirational phrasing
**Создано / обновлено:** 2026-09-23 19:58:09.189566+00 / 2026-09-24 05:05:38.621539+00

Компоненты оценки:
- **buyer_desire**: 7.90 (confidence 0.700). purchase_trigger_v2 preliminary score; gate passed; trigger=competence_pride Дата: 2026-09-23 19:59:53.152527+00.
- **clarity_at_glance**: 8.90 (confidence 0.760). purchase_trigger_v2 preliminary score; gate passed; trigger=competence_pride Дата: 2026-09-23 19:59:53.152527+00.
- **distinctiveness**: 7.70 (confidence 0.700). purchase_trigger_v2 preliminary score; gate passed; trigger=competence_pride Дата: 2026-09-23 19:59:53.152527+00.
- **giftability**: 7.80 (confidence 0.670). purchase_trigger_v2 preliminary score; gate passed; trigger=competence_pride Дата: 2026-09-23 19:59:53.152527+00.
- **insider_resonance**: 8.50 (confidence 0.720). purchase_trigger_v2 preliminary score; gate passed; trigger=competence_pride Дата: 2026-09-23 19:59:53.152527+00.
- **ip_safety**: 8.90 (confidence 0.600). purchase_trigger_v2 preliminary score; gate passed; trigger=competence_pride Дата: 2026-09-23 19:59:53.152527+00.
- **niche_fit**: 9.10 (confidence 0.720). purchase_trigger_v2 preliminary score; gate passed; trigger=competence_pride Дата: 2026-09-23 19:59:53.152527+00.
- **visual_potential**: 8.50 (confidence 0.720). purchase_trigger_v2 preliminary score; gate passed; trigger=competence_pride Дата: 2026-09-23 19:59:53.152527+00.

#### Cytology — find the weird one
`v4_cyto_weird_one` · ID `1dbfef72-7ed3-423a-a04d-0ce0fb02bff8`

**Интерпретация:** Исследовательский кандидат; одобрение владельца не зафиксировано
**Статус БД:** scored · **балл:** 88.29 · **confidence:** 70.32 · **coverage:** 100.00
**Текст / хук:** I FIND THE WEIRD ONE.
**Идея:** Simple pride in spotting the one cell that does not belong.
**Покупатель:** Cytotechnologists / cytologists
**Причина покупки:** Compact identity signal with obvious visual possibilities and gift appeal.
**Отличие:** No taxonomy list; the idea is pattern recognition.
**Визуальное направление:** Field of normal stylized cells with one odd cell circled.
**Создано / обновлено:** 2026-09-23 19:58:09.189566+00 / 2026-09-24 05:05:38.621539+00

Компоненты оценки:
- **buyer_desire**: 8.60 (confidence 0.700). purchase_trigger_v2 preliminary score; gate passed; trigger=pattern_recognition_pride Дата: 2026-09-23 19:59:53.152527+00.
- **clarity_at_glance**: 9.00 (confidence 0.760). purchase_trigger_v2 preliminary score; gate passed; trigger=pattern_recognition_pride Дата: 2026-09-23 19:59:53.152527+00.
- **distinctiveness**: 8.70 (confidence 0.700). purchase_trigger_v2 preliminary score; gate passed; trigger=pattern_recognition_pride Дата: 2026-09-23 19:59:53.152527+00.
- **giftability**: 8.40 (confidence 0.670). purchase_trigger_v2 preliminary score; gate passed; trigger=pattern_recognition_pride Дата: 2026-09-23 19:59:53.152527+00.
- **insider_resonance**: 9.10 (confidence 0.720). purchase_trigger_v2 preliminary score; gate passed; trigger=pattern_recognition_pride Дата: 2026-09-23 19:59:53.152527+00.
- **ip_safety**: 8.90 (confidence 0.600). purchase_trigger_v2 preliminary score; gate passed; trigger=pattern_recognition_pride Дата: 2026-09-23 19:59:53.152527+00.
- **niche_fit**: 9.40 (confidence 0.720). purchase_trigger_v2 preliminary score; gate passed; trigger=pattern_recognition_pride Дата: 2026-09-23 19:59:53.152527+00.
- **visual_potential**: 9.20 (confidence 0.720). purchase_trigger_v2 preliminary score; gate passed; trigger=pattern_recognition_pride Дата: 2026-09-23 19:59:53.152527+00.

## 12. Dental Laboratory Technician
Ключ: `dental_laboratory_technician` · ID: `4da340c1-db6b-4f9e-8a44-cc05b7485db9`

**Статус БД:** scored · **балл:** 72.20 · **confidence:** 76.08 · **coverage:** 100.00
**Аудитория:** Dental laboratory technicians fabricating crowns, bridges, dentures and appliances
**Категория:** occupational_identity
**Исследовательская аргументация:** Declining employment but highly tangible craft identity around models, crowns, shade, wax, ceramic and fabrication. Etsy has a modest dedicated market rather than a mass category.
**Создано / обновлено:** 2026-09-23 09:56:40.513406+00 / 2026-09-23 09:56:40.513406+00

### Компоненты оценки ниши

- **channel_breadth**: 7.00 (confidence 0.560). Forge diversity-batch v3 score using current 2025-35 BLS/O*NET evidence plus sampled current Etsy competition. Where exact marketplace counts were unavailable, competition confidence is intentionally lower. Дата: 2026-09-23 09:56:40.513406+00.
- **competition_opportunity**: 6.50 (confidence 0.840). Forge diversity-batch v3 score using current 2025-35 BLS/O*NET evidence plus sampled current Etsy competition. Where exact marketplace counts were unavailable, competition confidence is intentionally lower. Дата: 2026-09-23 09:56:40.513406+00.
- **concept_depth**: 9.00 (confidence 0.780). Forge diversity-batch v3 score using current 2025-35 BLS/O*NET evidence plus sampled current Etsy competition. Where exact marketplace counts were unavailable, competition confidence is intentionally lower. Дата: 2026-09-23 09:56:40.513406+00.
- **demand_evidence**: 5.50 (confidence 0.920). Forge diversity-batch v3 score using current 2025-35 BLS/O*NET evidence plus sampled current Etsy competition. Where exact marketplace counts were unavailable, competition confidence is intentionally lower. Дата: 2026-09-23 09:56:40.513406+00.
- **founder_edge**: 2.00 (confidence 0.400). Forge diversity-batch v3 score using current 2025-35 BLS/O*NET evidence plus sampled current Etsy competition. Where exact marketplace counts were unavailable, competition confidence is intentionally lower. Дата: 2026-09-23 09:56:40.513406+00.
- **identity_intensity**: 8.00 (confidence 0.720). Forge diversity-batch v3 score using current 2025-35 BLS/O*NET evidence plus sampled current Etsy competition. Where exact marketplace counts were unavailable, competition confidence is intentionally lower. Дата: 2026-09-23 09:56:40.513406+00.
- **legal_safety**: 8.50 (confidence 0.640). Forge diversity-batch v3 score using current 2025-35 BLS/O*NET evidence plus sampled current Etsy competition. Where exact marketplace counts were unavailable, competition confidence is intentionally lower. Дата: 2026-09-23 09:56:40.513406+00.
- **purchase_motivation**: 7.50 (confidence 0.660). Forge diversity-batch v3 score using current 2025-35 BLS/O*NET evidence plus sampled current Etsy competition. Where exact marketplace counts were unavailable, competition confidence is intentionally lower. Дата: 2026-09-23 09:56:40.513406+00.
- **repeatability**: 7.50 (confidence 0.620). Forge diversity-batch v3 score using current 2025-35 BLS/O*NET evidence plus sampled current Etsy competition. Where exact marketplace counts were unavailable, competition confidence is intentionally lower. Дата: 2026-09-23 09:56:40.513406+00.
- **visual_language**: 9.00 (confidence 0.800). Forge diversity-batch v3 score using current 2025-35 BLS/O*NET evidence plus sampled current Etsy competition. Where exact marketplace counts were unavailable, competition confidence is intentionally lower. Дата: 2026-09-23 09:56:40.513406+00.

### Концепции (0)

## 13. Diagnostic Medical Sonographer
Ключ: `diagnostic_medical_sonographer` · ID: `0cbf9c6f-fa26-4a54-9fba-98b5e65c8cd8`

**Статус БД:** scored · **балл:** 78.00 · **confidence:** 81.72 · **coverage:** 100.00
**Аудитория:** Diagnostic medical sonographers / ultrasound technologists
**Категория:** occupational_identity
**Исследовательская аргументация:** Large, fast-growing, highly identifiable occupation with strong visual language, but Etsy already shows substantial sonography competition. Retain mainly as a high-demand/high-competition benchmark unless a materially different insider concept emerges.
**Создано / обновлено:** 2026-09-23 09:42:54.27545+00 / 2026-09-23 09:43:36.792084+00

### Компоненты оценки ниши

- **channel_breadth**: 8.00 (confidence 0.680). Forge hidden-trades v2 initial score using current BLS/O*NET occupational evidence plus sampled Etsy marketplace depth. Scores prioritize buyer identity and whitespace, not raw occupation size. Benchmark niches intentionally receive competition penalties. Дата: 2026-09-23 09:43:36.792084+00.
- **competition_opportunity**: 2.50 (confidence 0.920). Forge hidden-trades v2 initial score using current BLS/O*NET occupational evidence plus sampled Etsy marketplace depth. Scores prioritize buyer identity and whitespace, not raw occupation size. Benchmark niches intentionally receive competition penalties. Дата: 2026-09-23 09:43:36.792084+00.
- **concept_depth**: 8.50 (confidence 0.760). Forge hidden-trades v2 initial score using current BLS/O*NET occupational evidence plus sampled Etsy marketplace depth. Scores prioritize buyer identity and whitespace, not raw occupation size. Benchmark niches intentionally receive competition penalties. Дата: 2026-09-23 09:43:36.792084+00.
- **demand_evidence**: 9.00 (confidence 0.920). Forge hidden-trades v2 initial score using current BLS/O*NET occupational evidence plus sampled Etsy marketplace depth. Scores prioritize buyer identity and whitespace, not raw occupation size. Benchmark niches intentionally receive competition penalties. Дата: 2026-09-23 09:43:36.792084+00.
- **founder_edge**: 2.00 (confidence 0.400). Forge hidden-trades v2 initial score using current BLS/O*NET occupational evidence plus sampled Etsy marketplace depth. Scores prioritize buyer identity and whitespace, not raw occupation size. Benchmark niches intentionally receive competition penalties. Дата: 2026-09-23 09:43:36.792084+00.
- **identity_intensity**: 9.00 (confidence 0.800). Forge hidden-trades v2 initial score using current BLS/O*NET occupational evidence plus sampled Etsy marketplace depth. Scores prioritize buyer identity and whitespace, not raw occupation size. Benchmark niches intentionally receive competition penalties. Дата: 2026-09-23 09:43:36.792084+00.
- **legal_safety**: 8.50 (confidence 0.660). Forge hidden-trades v2 initial score using current BLS/O*NET occupational evidence plus sampled Etsy marketplace depth. Scores prioritize buyer identity and whitespace, not raw occupation size. Benchmark niches intentionally receive competition penalties. Дата: 2026-09-23 09:43:36.792084+00.
- **purchase_motivation**: 9.00 (confidence 0.780). Forge hidden-trades v2 initial score using current BLS/O*NET occupational evidence plus sampled Etsy marketplace depth. Scores prioritize buyer identity and whitespace, not raw occupation size. Benchmark niches intentionally receive competition penalties. Дата: 2026-09-23 09:43:36.792084+00.
- **repeatability**: 9.00 (confidence 0.760). Forge hidden-trades v2 initial score using current BLS/O*NET occupational evidence plus sampled Etsy marketplace depth. Scores prioritize buyer identity and whitespace, not raw occupation size. Benchmark niches intentionally receive competition penalties. Дата: 2026-09-23 09:43:36.792084+00.
- **visual_language**: 9.50 (confidence 0.840). Forge hidden-trades v2 initial score using current BLS/O*NET occupational evidence plus sampled Etsy marketplace depth. Scores prioritize buyer identity and whitespace, not raw occupation size. Benchmark niches intentionally receive competition penalties. Дата: 2026-09-23 09:43:36.792084+00.

### Концепции (0)

## 14. Electrical / Electronic Engineering Technician
Ключ: `electrical_electronic_engineering_technician` · ID: `b2c88bf5-9589-47ae-98dd-be8af6621208`

**Статус БД:** shortlisted · **балл:** 80.35 · **confidence:** 67.30 · **coverage:** 100.00
**Аудитория:** Electrical and electronic engineering technologists and technicians
**Категория:** occupational_identity
**Исследовательская аргументация:** Large technical occupation spanning labs, factories, utilities and electronics manufacturing. Strong visual depth around prototypes, test equipment, circuits, calibration and fault finding; exact occupational merch appeared sparse in sampled search.
**Создано / обновлено:** 2026-09-23 09:56:40.513406+00 / 2026-09-23 10:03:30.159451+00

### Компоненты оценки ниши

- **channel_breadth**: 8.50 (confidence 0.660). Forge diversity-batch v3 score using current 2025-35 BLS/O*NET evidence plus sampled current Etsy competition. Where exact marketplace counts were unavailable, competition confidence is intentionally lower. Дата: 2026-09-23 09:56:40.513406+00.
- **competition_opportunity**: 8.00 (confidence 0.480). Forge diversity-batch v3 score using current 2025-35 BLS/O*NET evidence plus sampled current Etsy competition. Where exact marketplace counts were unavailable, competition confidence is intentionally lower. Дата: 2026-09-23 09:56:40.513406+00.
- **concept_depth**: 9.00 (confidence 0.720). Forge diversity-batch v3 score using current 2025-35 BLS/O*NET evidence plus sampled current Etsy competition. Where exact marketplace counts were unavailable, competition confidence is intentionally lower. Дата: 2026-09-23 09:56:40.513406+00.
- **demand_evidence**: 8.50 (confidence 0.920). Forge diversity-batch v3 score using current 2025-35 BLS/O*NET evidence plus sampled current Etsy competition. Where exact marketplace counts were unavailable, competition confidence is intentionally lower. Дата: 2026-09-23 09:56:40.513406+00.
- **founder_edge**: 2.00 (confidence 0.400). Forge diversity-batch v3 score using current 2025-35 BLS/O*NET evidence plus sampled current Etsy competition. Where exact marketplace counts were unavailable, competition confidence is intentionally lower. Дата: 2026-09-23 09:56:40.513406+00.
- **identity_intensity**: 7.50 (confidence 0.620). Forge diversity-batch v3 score using current 2025-35 BLS/O*NET evidence plus sampled current Etsy competition. Where exact marketplace counts were unavailable, competition confidence is intentionally lower. Дата: 2026-09-23 09:56:40.513406+00.
- **legal_safety**: 8.50 (confidence 0.640). Forge diversity-batch v3 score using current 2025-35 BLS/O*NET evidence plus sampled current Etsy competition. Where exact marketplace counts were unavailable, competition confidence is intentionally lower. Дата: 2026-09-23 09:56:40.513406+00.
- **purchase_motivation**: 7.00 (confidence 0.560). Forge diversity-batch v3 score using current 2025-35 BLS/O*NET evidence plus sampled current Etsy competition. Where exact marketplace counts were unavailable, competition confidence is intentionally lower. Дата: 2026-09-23 09:56:40.513406+00.
- **repeatability**: 8.00 (confidence 0.620). Forge diversity-batch v3 score using current 2025-35 BLS/O*NET evidence plus sampled current Etsy competition. Where exact marketplace counts were unavailable, competition confidence is intentionally lower. Дата: 2026-09-23 09:56:40.513406+00.
- **visual_language**: 9.50 (confidence 0.780). Forge diversity-batch v3 score using current 2025-35 BLS/O*NET evidence plus sampled current Etsy competition. Where exact marketplace counts were unavailable, competition confidence is intentionally lower. Дата: 2026-09-23 09:56:40.513406+00.

### Концепции (16)

#### Electronics Tech — blueprint / wiring / circuit / log
`eet_blueprint_wiring_circuit_log` · ID `d64f89c7-e3cf-4760-b6e6-f0f4b7a7b738`

**Интерпретация:** Исследовательский кандидат; одобрение владельца не зафиксировано
**Статус БД:** scored · **балл:** 87.55 · **confidence:** 68.17 · **coverage:** 100.00
**Текст / хук:** BLUEPRINT • WIRING • CIRCUIT • LOG
**Идея:** Electronics Tech — blueprint / wiring / circuit / log. Core hook: BLUEPRINT • WIRING • CIRCUIT • LOG. Grounded in current occupational tasks and intended as insider identity art, not operating/medical instruction. Avoid employer, OEM, certification-body and proprietary-interface branding.
**Покупатель:** Electrical and electronic engineering technologists and technicians
**Причина покупки:** Professional identity purchase for electrical and electronic engineering technologists and technicians who recognize the real tools, measurements and workflow.
**Отличие:** Technical technical map direction designed to avoid generic job-title, floral, retro-badge and parody templates.
**Визуальное направление:** Documentation-centric electronics identity referencing plans, wiring, circuitry and logs.
**Создано / обновлено:** 2026-09-23 10:02:18.463532+00 / 2026-09-23 10:02:33.245254+00

Компоненты оценки:
- **buyer_desire**: 8.26 (confidence 0.670). Provisional Forge challenger-concept score derived from occupationally grounded concept archetype plus the fully scored niche prior. It is a research-priority score, not a sales forecast or legal clearance. Дата: 2026-09-23 10:02:33.245254+00.
- **clarity_at_glance**: 7.73 (confidence 0.670). Provisional Forge challenger-concept score derived from occupationally grounded concept archetype plus the fully scored niche prior. It is a research-priority score, not a sales forecast or legal clearance. Дата: 2026-09-23 10:02:33.245254+00.
- **distinctiveness**: 9.10 (confidence 0.670). Provisional Forge challenger-concept score derived from occupationally grounded concept archetype plus the fully scored niche prior. It is a research-priority score, not a sales forecast or legal clearance. Дата: 2026-09-23 10:02:33.245254+00.
- **giftability**: 7.43 (confidence 0.670). Provisional Forge challenger-concept score derived from occupationally grounded concept archetype plus the fully scored niche prior. It is a research-priority score, not a sales forecast or legal clearance. Дата: 2026-09-23 10:02:33.245254+00.
- **insider_resonance**: 9.25 (confidence 0.700). Provisional Forge challenger-concept score derived from occupationally grounded concept archetype plus the fully scored niche prior. It is a research-priority score, not a sales forecast or legal clearance. Дата: 2026-09-23 10:02:33.245254+00.
- **ip_safety**: 8.60 (confidence 0.670). Provisional Forge challenger-concept score derived from occupationally grounded concept archetype plus the fully scored niche prior. It is a research-priority score, not a sales forecast or legal clearance. Дата: 2026-09-23 10:02:33.245254+00.
- **niche_fit**: 9.35 (confidence 0.700). Provisional Forge challenger-concept score derived from occupationally grounded concept archetype plus the fully scored niche prior. It is a research-priority score, not a sales forecast or legal clearance. Дата: 2026-09-23 10:02:33.245254+00.
- **visual_potential**: 9.55 (confidence 0.700). Provisional Forge challenger-concept score derived from occupationally grounded concept archetype plus the fully scored niche prior. It is a research-priority score, not a sales forecast or legal clearance. Дата: 2026-09-23 10:02:33.245254+00.

#### Electronics Tech — board / circuit / test point / result
`eet_board_circuit_testpoint_result` · ID `d68ed1a8-4c07-46e7-861d-35771f2abe77`

**Интерпретация:** Исследовательский кандидат; одобрение владельца не зафиксировано
**Статус БД:** scored · **балл:** 88.17 · **confidence:** 68.17 · **coverage:** 100.00
**Текст / хук:** BOARD • CIRCUIT • TEST POINT • RESULT
**Идея:** Electronics Tech — board / circuit / test point / result. Core hook: BOARD • CIRCUIT • TEST POINT • RESULT. Grounded in current occupational tasks and intended as insider identity art, not operating/medical instruction. Avoid employer, OEM, certification-body and proprietary-interface branding.
**Покупатель:** Electrical and electronic engineering technologists and technicians
**Причина покупки:** Professional identity purchase for electrical and electronic engineering technologists and technicians who recognize the real tools, measurements and workflow.
**Отличие:** Technical technical map direction designed to avoid generic job-title, floral, retro-badge and parody templates.
**Визуальное направление:** Original PCB/test-point composition focused on technician measurement and evaluation.
**Создано / обновлено:** 2026-09-23 10:02:18.463532+00 / 2026-09-23 10:02:33.245254+00

Компоненты оценки:
- **buyer_desire**: 8.36 (confidence 0.670). Provisional Forge challenger-concept score derived from occupationally grounded concept archetype plus the fully scored niche prior. It is a research-priority score, not a sales forecast or legal clearance. Дата: 2026-09-23 10:02:33.245254+00.
- **clarity_at_glance**: 7.77 (confidence 0.670). Provisional Forge challenger-concept score derived from occupationally grounded concept archetype plus the fully scored niche prior. It is a research-priority score, not a sales forecast or legal clearance. Дата: 2026-09-23 10:02:33.245254+00.
- **distinctiveness**: 9.20 (confidence 0.670). Provisional Forge challenger-concept score derived from occupationally grounded concept archetype plus the fully scored niche prior. It is a research-priority score, not a sales forecast or legal clearance. Дата: 2026-09-23 10:02:33.245254+00.
- **giftability**: 7.47 (confidence 0.670). Provisional Forge challenger-concept score derived from occupationally grounded concept archetype plus the fully scored niche prior. It is a research-priority score, not a sales forecast or legal clearance. Дата: 2026-09-23 10:02:33.245254+00.
- **insider_resonance**: 9.30 (confidence 0.700). Provisional Forge challenger-concept score derived from occupationally grounded concept archetype plus the fully scored niche prior. It is a research-priority score, not a sales forecast or legal clearance. Дата: 2026-09-23 10:02:33.245254+00.
- **ip_safety**: 8.60 (confidence 0.670). Provisional Forge challenger-concept score derived from occupationally grounded concept archetype plus the fully scored niche prior. It is a research-priority score, not a sales forecast or legal clearance. Дата: 2026-09-23 10:02:33.245254+00.
- **niche_fit**: 9.35 (confidence 0.700). Provisional Forge challenger-concept score derived from occupationally grounded concept archetype plus the fully scored niche prior. It is a research-priority score, not a sales forecast or legal clearance. Дата: 2026-09-23 10:02:33.245254+00.
- **visual_potential**: 9.60 (confidence 0.700). Provisional Forge challenger-concept score derived from occupationally grounded concept archetype plus the fully scored niche prior. It is a research-priority score, not a sales forecast or legal clearance. Дата: 2026-09-23 10:02:33.245254+00.

#### Electronics Tech — board / connector / continuity
`eet_board_connector_continuity` · ID `121328c9-ec9f-46f5-b036-3ccd8baeb8d9`

**Интерпретация:** Исследовательский кандидат; одобрение владельца не зафиксировано
**Статус БД:** scored · **балл:** 88.52 · **confidence:** 71.06 · **coverage:** 100.00
**Текст / хук:** BOARD • CONNECTOR • CONTINUITY
**Идея:** BOARD • CONNECTOR • CONTINUITY with a generic PCB/connector continuity path and test-point motifs.
**Покупатель:** Electrical and electronic engineering technologists and technicians
**Причина покупки:** Hands-on electronics troubleshooting identity.
**Отличие:** Specific bench-work visual rather than broad electrical engineering merch.
**Визуальное направление:** Generic PCB/connector continuity map.
**Создано / обновлено:** 2026-09-23 09:59:11.838032+00 / 2026-09-23 09:59:11.838032+00

Компоненты оценки:
- **buyer_desire**: 8.32 (confidence 0.708). Unified Forge diversity-v3 concept score grounded in current occupational tasks and niche evidence. No visual generated; phrase/IP review remains separate. Дата: 2026-09-23 09:59:11.838032+00.
- **clarity_at_glance**: 7.80 (confidence 0.678). Unified Forge diversity-v3 concept score grounded in current occupational tasks and niche evidence. No visual generated; phrase/IP review remains separate. Дата: 2026-09-23 09:59:11.838032+00.
- **distinctiveness**: 9.30 (confidence 0.723). Unified Forge diversity-v3 concept score grounded in current occupational tasks and niche evidence. No visual generated; phrase/IP review remains separate. Дата: 2026-09-23 09:59:11.838032+00.
- **giftability**: 7.32 (confidence 0.663). Unified Forge diversity-v3 concept score grounded in current occupational tasks and niche evidence. No visual generated; phrase/IP review remains separate. Дата: 2026-09-23 09:59:11.838032+00.
- **insider_resonance**: 9.30 (confidence 0.738). Unified Forge diversity-v3 concept score grounded in current occupational tasks and niche evidence. No visual generated; phrase/IP review remains separate. Дата: 2026-09-23 09:59:11.838032+00.
- **ip_safety**: 8.80 (confidence 0.550). Unified Forge diversity-v3 concept score grounded in current occupational tasks and niche evidence. No visual generated; phrase/IP review remains separate. Дата: 2026-09-23 09:59:11.838032+00.
- **niche_fit**: 9.52 (confidence 0.738). Unified Forge diversity-v3 concept score grounded in current occupational tasks and niche evidence. No visual generated; phrase/IP review remains separate. Дата: 2026-09-23 09:59:11.838032+00.
- **visual_potential**: 9.70 (confidence 0.753). Unified Forge diversity-v3 concept score grounded in current occupational tasks and niche evidence. No visual generated; phrase/IP review remains separate. Дата: 2026-09-23 09:59:11.838032+00.

#### Electronics Tech — build / test / troubleshoot / document
`eet_build_test_troubleshoot_document` · ID `61993682-e13b-445d-8929-c7ac474e7983`

**Интерпретация:** Исследовательский кандидат; одобрение владельца не зафиксировано
**Статус БД:** scored · **балл:** 89.36 · **confidence:** 69.17 · **coverage:** 100.00
**Текст / хук:** BUILD • TEST • TROUBLESHOOT • DOCUMENT
**Идея:** Electronics Tech — build / test / troubleshoot / document. Core hook: BUILD • TEST • TROUBLESHOOT • DOCUMENT. Grounded in current occupational tasks and intended as insider identity art, not operating/medical instruction. Avoid employer, OEM, certification-body and proprietary-interface branding.
**Покупатель:** Electrical and electronic engineering technologists and technicians
**Причина покупки:** Professional identity purchase for electrical and electronic engineering technologists and technicians who recognize the real tools, measurements and workflow.
**Отличие:** Technical diagnostic direction designed to avoid generic job-title, floral, retro-badge and parody templates.
**Визуальное направление:** Bench-to-record technical workflow with generic board, meter and log cues.
**Создано / обновлено:** 2026-09-23 10:02:18.463532+00 / 2026-09-23 10:05:50.016716+00

Компоненты оценки:
- **buyer_desire**: 8.76 (confidence 0.680). Provisional Forge challenger-concept score derived from occupationally grounded concept archetype plus the fully scored niche prior. It is a research-priority score, not a sales forecast or legal clearance. Дата: 2026-09-23 10:02:33.245254+00.
- **clarity_at_glance**: 8.60 (confidence 0.680). Provisional Forge challenger-concept score derived from occupationally grounded concept archetype plus the fully scored niche prior. It is a research-priority score, not a sales forecast or legal clearance. Дата: 2026-09-23 10:02:33.245254+00.
- **distinctiveness**: 9.10 (confidence 0.680). Provisional Forge challenger-concept score derived from occupationally grounded concept archetype plus the fully scored niche prior. It is a research-priority score, not a sales forecast or legal clearance. Дата: 2026-09-23 10:02:33.245254+00.
- **giftability**: 7.90 (confidence 0.680). Provisional Forge challenger-concept score derived from occupationally grounded concept archetype plus the fully scored niche prior. It is a research-priority score, not a sales forecast or legal clearance. Дата: 2026-09-23 10:02:33.245254+00.
- **insider_resonance**: 9.45 (confidence 0.710). Provisional Forge challenger-concept score derived from occupationally grounded concept archetype plus the fully scored niche prior. It is a research-priority score, not a sales forecast or legal clearance. Дата: 2026-09-23 10:02:33.245254+00.
- **ip_safety**: 8.70 (confidence 0.680). Provisional Forge challenger-concept score derived from occupationally grounded concept archetype plus the fully scored niche prior. It is a research-priority score, not a sales forecast or legal clearance. Дата: 2026-09-23 10:02:33.245254+00.
- **niche_fit**: 9.45 (confidence 0.710). Provisional Forge challenger-concept score derived from occupationally grounded concept archetype plus the fully scored niche prior. It is a research-priority score, not a sales forecast or legal clearance. Дата: 2026-09-23 10:02:33.245254+00.
- **visual_potential**: 8.95 (confidence 0.710). Provisional Forge challenger-concept score derived from occupationally grounded concept archetype plus the fully scored niche prior. It is a research-priority score, not a sales forecast or legal clearance. Дата: 2026-09-23 10:02:33.245254+00.

#### Electronics Tech — calibrate / repair / verify
`eet_calibrate_repair_verify` · ID `48bb2bb1-5846-4615-b67e-511c1b03ae16`

**Интерпретация:** Исследовательский кандидат; одобрение владельца не зафиксировано
**Статус БД:** scored · **балл:** 88.05 · **confidence:** 70.47 · **coverage:** 100.00
**Текст / хук:** CALIBRATE • REPAIR • VERIFY
**Идея:** CALIBRATE • REPAIR • VERIFY as a technical service loop reflecting calibration, repair and verification of instruments/testing equipment.
**Покупатель:** Electrical and electronic engineering technologists and technicians
**Причина покупки:** Clear service identity with strong giftability.
**Отличие:** Specific engineering-technician workflow instead of broad engineer branding.
**Визуальное направление:** Generic instrument service loop.
**Создано / обновлено:** 2026-09-23 09:59:11.838032+00 / 2026-09-23 09:59:11.838032+00

Компоненты оценки:
- **buyer_desire**: 8.62 (confidence 0.716). Unified Forge diversity-v3 concept score grounded in current occupational tasks and niche evidence. No visual generated; phrase/IP review remains separate. Дата: 2026-09-23 09:59:11.838032+00.
- **clarity_at_glance**: 9.40 (confidence 0.746). Unified Forge diversity-v3 concept score grounded in current occupational tasks and niche evidence. No visual generated; phrase/IP review remains separate. Дата: 2026-09-23 09:59:11.838032+00.
- **distinctiveness**: 8.70 (confidence 0.701). Unified Forge diversity-v3 concept score grounded in current occupational tasks and niche evidence. No visual generated; phrase/IP review remains separate. Дата: 2026-09-23 09:59:11.838032+00.
- **giftability**: 8.42 (confidence 0.693). Unified Forge diversity-v3 concept score grounded in current occupational tasks and niche evidence. No visual generated; phrase/IP review remains separate. Дата: 2026-09-23 09:59:11.838032+00.
- **insider_resonance**: 9.00 (confidence 0.723). Unified Forge diversity-v3 concept score grounded in current occupational tasks and niche evidence. No visual generated; phrase/IP review remains separate. Дата: 2026-09-23 09:59:11.838032+00.
- **ip_safety**: 9.10 (confidence 0.550). Unified Forge diversity-v3 concept score grounded in current occupational tasks and niche evidence. No visual generated; phrase/IP review remains separate. Дата: 2026-09-23 09:59:11.838032+00.
- **niche_fit**: 9.32 (confidence 0.731). Unified Forge diversity-v3 concept score grounded in current occupational tasks and niche evidence. No visual generated; phrase/IP review remains separate. Дата: 2026-09-23 09:59:11.838032+00.
- **visual_potential**: 8.50 (confidence 0.693). Unified Forge diversity-v3 concept score grounded in current occupational tasks and niche evidence. No visual generated; phrase/IP review remains separate. Дата: 2026-09-23 09:59:11.838032+00.

#### Electronics Tech — power / signal / control / load
`eet_power_signal_control_load` · ID `f93b7b97-1751-4a77-bc12-becab7e22a62`

**Интерпретация:** Исследовательский кандидат; одобрение владельца не зафиксировано
**Статус БД:** scored · **балл:** 88.78 · **confidence:** 69.17 · **coverage:** 100.00
**Текст / хук:** POWER • SIGNAL • CONTROL • LOAD
**Идея:** Electronics Tech — power / signal / control / load. Core hook: POWER • SIGNAL • CONTROL • LOAD. Grounded in current occupational tasks and intended as insider identity art, not operating/medical instruction. Avoid employer, OEM, certification-body and proprietary-interface branding.
**Покупатель:** Electrical and electronic engineering technologists and technicians
**Причина покупки:** Professional identity purchase for electrical and electronic engineering technologists and technicians who recognize the real tools, measurements and workflow.
**Отличие:** Technical system map direction designed to avoid generic job-title, floral, retro-badge and parody templates.
**Визуальное направление:** Four-domain electrical/electronic systems identity; original circuit blocks, no vendor symbols copied.
**Создано / обновлено:** 2026-09-23 10:02:18.463532+00 / 2026-09-23 10:03:30.159451+00

Компоненты оценки:
- **buyer_desire**: 8.56 (confidence 0.680). Provisional Forge challenger-concept score derived from occupationally grounded concept archetype plus the fully scored niche prior. It is a research-priority score, not a sales forecast or legal clearance. Дата: 2026-09-23 10:02:33.245254+00.
- **clarity_at_glance**: 8.20 (confidence 0.680). Provisional Forge challenger-concept score derived from occupationally grounded concept archetype plus the fully scored niche prior. It is a research-priority score, not a sales forecast or legal clearance. Дата: 2026-09-23 10:02:33.245254+00.
- **distinctiveness**: 9.10 (confidence 0.680). Provisional Forge challenger-concept score derived from occupationally grounded concept archetype plus the fully scored niche prior. It is a research-priority score, not a sales forecast or legal clearance. Дата: 2026-09-23 10:02:33.245254+00.
- **giftability**: 7.60 (confidence 0.680). Provisional Forge challenger-concept score derived from occupationally grounded concept archetype plus the fully scored niche prior. It is a research-priority score, not a sales forecast or legal clearance. Дата: 2026-09-23 10:02:33.245254+00.
- **insider_resonance**: 9.15 (confidence 0.710). Provisional Forge challenger-concept score derived from occupationally grounded concept archetype plus the fully scored niche prior. It is a research-priority score, not a sales forecast or legal clearance. Дата: 2026-09-23 10:02:33.245254+00.
- **ip_safety**: 8.80 (confidence 0.680). Provisional Forge challenger-concept score derived from occupationally grounded concept archetype plus the fully scored niche prior. It is a research-priority score, not a sales forecast or legal clearance. Дата: 2026-09-23 10:02:33.245254+00.
- **niche_fit**: 9.35 (confidence 0.710). Provisional Forge challenger-concept score derived from occupationally grounded concept archetype plus the fully scored niche prior. It is a research-priority score, not a sales forecast or legal clearance. Дата: 2026-09-23 10:02:33.245254+00.
- **visual_potential**: 9.65 (confidence 0.710). Provisional Forge challenger-concept score derived from occupationally grounded concept archetype plus the fully scored niche prior. It is a research-priority score, not a sales forecast or legal clearance. Дата: 2026-09-23 10:02:33.245254+00.

#### Electronics Tech — prototype / test / troubleshoot
`eet_prototype_assemble_test_troubleshoot` · ID `8ba22688-dc97-427e-9bd0-21540146bc67`

**Интерпретация:** Исторический: семантический дубликат
**Статус БД:** paused · **балл:** 88.05 · **confidence:** 70.47 · **coverage:** 100.00
**Текст / хук:** ASSEMBLE • TEST • TROUBLESHOOT
**Идея:** ASSEMBLE • TEST • TROUBLESHOOT grounded in BLS duties for electrical/electronic engineering technologists and technicians.
**Покупатель:** Electrical and electronic engineering technologists and technicians
**Причина покупки:** Technical bench/prototype identity with broad applicability.
**Отличие:** Avoids generic engineer jokes and electrician imagery.
**Визуальное направление:** Bench/prototype workflow with generic components.
**semantic_duplicate_of:** eet_build_test_troubleshoot_document
**semantic_duplicate_reason:** Same build/assemble + test + troubleshoot workflow; challenger scores higher and adds documentation.
**Создано / обновлено:** 2026-09-23 09:59:11.838032+00 / 2026-09-23 10:05:50.016716+00

Компоненты оценки:
- **buyer_desire**: 8.62 (confidence 0.716). Unified Forge diversity-v3 concept score grounded in current occupational tasks and niche evidence. No visual generated; phrase/IP review remains separate. Дата: 2026-09-23 09:59:11.838032+00.
- **clarity_at_glance**: 9.40 (confidence 0.746). Unified Forge diversity-v3 concept score grounded in current occupational tasks and niche evidence. No visual generated; phrase/IP review remains separate. Дата: 2026-09-23 09:59:11.838032+00.
- **distinctiveness**: 8.70 (confidence 0.701). Unified Forge diversity-v3 concept score grounded in current occupational tasks and niche evidence. No visual generated; phrase/IP review remains separate. Дата: 2026-09-23 09:59:11.838032+00.
- **giftability**: 8.42 (confidence 0.693). Unified Forge diversity-v3 concept score grounded in current occupational tasks and niche evidence. No visual generated; phrase/IP review remains separate. Дата: 2026-09-23 09:59:11.838032+00.
- **insider_resonance**: 9.00 (confidence 0.723). Unified Forge diversity-v3 concept score grounded in current occupational tasks and niche evidence. No visual generated; phrase/IP review remains separate. Дата: 2026-09-23 09:59:11.838032+00.
- **ip_safety**: 9.10 (confidence 0.550). Unified Forge diversity-v3 concept score grounded in current occupational tasks and niche evidence. No visual generated; phrase/IP review remains separate. Дата: 2026-09-23 09:59:11.838032+00.
- **niche_fit**: 9.32 (confidence 0.731). Unified Forge diversity-v3 concept score grounded in current occupational tasks and niche evidence. No visual generated; phrase/IP review remains separate. Дата: 2026-09-23 09:59:11.838032+00.
- **visual_potential**: 8.50 (confidence 0.693). Unified Forge diversity-v3 concept score grounded in current occupational tasks and niche evidence. No visual generated; phrase/IP review remains separate. Дата: 2026-09-23 09:59:11.838032+00.

#### Electronics Tech — prototype / measure / correct / verify
`eet_prototype_measure_correct_verify` · ID `b392a8f0-2fab-4ff4-87cb-15d60eddb1ae`

**Интерпретация:** Исследовательский кандидат; одобрение владельца не зафиксировано
**Статус БД:** scored · **балл:** 88.75 · **confidence:** 69.17 · **coverage:** 100.00
**Текст / хук:** PROTOTYPE → MEASURE → CORRECT → VERIFY
**Идея:** Electronics Tech — prototype / measure / correct / verify. Core hook: PROTOTYPE → MEASURE → CORRECT → VERIFY. Grounded in current occupational tasks and intended as insider identity art, not operating/medical instruction. Avoid employer, OEM, certification-body and proprietary-interface branding.
**Покупатель:** Electrical and electronic engineering technologists and technicians
**Причина покупки:** Professional identity purchase for electrical and electronic engineering technologists and technicians who recognize the real tools, measurements and workflow.
**Отличие:** Technical diagnostic direction designed to avoid generic job-title, floral, retro-badge and parody templates.
**Визуальное направление:** Engineering-support troubleshooting loop with original prototype/test imagery.
**Создано / обновлено:** 2026-09-23 10:02:18.463532+00 / 2026-09-23 10:02:33.245254+00

Компоненты оценки:
- **buyer_desire**: 8.66 (confidence 0.680). Provisional Forge challenger-concept score derived from occupationally grounded concept archetype plus the fully scored niche prior. It is a research-priority score, not a sales forecast or legal clearance. Дата: 2026-09-23 10:02:33.245254+00.
- **clarity_at_glance**: 8.57 (confidence 0.680). Provisional Forge challenger-concept score derived from occupationally grounded concept archetype plus the fully scored niche prior. It is a research-priority score, not a sales forecast or legal clearance. Дата: 2026-09-23 10:02:33.245254+00.
- **distinctiveness**: 9.00 (confidence 0.680). Provisional Forge challenger-concept score derived from occupationally grounded concept archetype plus the fully scored niche prior. It is a research-priority score, not a sales forecast or legal clearance. Дата: 2026-09-23 10:02:33.245254+00.
- **giftability**: 7.87 (confidence 0.680). Provisional Forge challenger-concept score derived from occupationally grounded concept archetype plus the fully scored niche prior. It is a research-priority score, not a sales forecast or legal clearance. Дата: 2026-09-23 10:02:33.245254+00.
- **insider_resonance**: 9.40 (confidence 0.710). Provisional Forge challenger-concept score derived from occupationally grounded concept archetype plus the fully scored niche prior. It is a research-priority score, not a sales forecast or legal clearance. Дата: 2026-09-23 10:02:33.245254+00.
- **ip_safety**: 8.70 (confidence 0.680). Provisional Forge challenger-concept score derived from occupationally grounded concept archetype plus the fully scored niche prior. It is a research-priority score, not a sales forecast or legal clearance. Дата: 2026-09-23 10:02:33.245254+00.
- **niche_fit**: 9.45 (confidence 0.710). Provisional Forge challenger-concept score derived from occupationally grounded concept archetype plus the fully scored niche prior. It is a research-priority score, not a sales forecast or legal clearance. Дата: 2026-09-23 10:02:33.245254+00.
- **visual_potential**: 8.90 (confidence 0.710). Provisional Forge challenger-concept score derived from occupationally grounded concept archetype plus the fully scored niche prior. It is a research-priority score, not a sales forecast or legal clearance. Дата: 2026-09-23 10:02:33.245254+00.

#### Electronics Tech — schematic to modification
`eet_schematic_assemble_test_modify` · ID `9da459eb-8649-4151-b18b-d93c635a0d0b`

**Интерпретация:** Исследовательский кандидат; одобрение владельца не зафиксировано
**Статус БД:** scored · **балл:** 86.27 · **confidence:** 67.17 · **coverage:** 100.00
**Текст / хук:** SCHEMATIC → ASSEMBLE → TEST → MODIFY
**Идея:** Electronics Tech — schematic to modification. Core hook: SCHEMATIC → ASSEMBLE → TEST → MODIFY. Grounded in current occupational tasks and intended as insider identity art, not operating/medical instruction. Avoid employer, OEM, certification-body and proprietary-interface branding.
**Покупатель:** Electrical and electronic engineering technologists and technicians
**Причина покупки:** Professional identity purchase for electrical and electronic engineering technologists and technicians who recognize the real tools, measurements and workflow.
**Отличие:** Technical workflow direction designed to avoid generic job-title, floral, retro-badge and parody templates.
**Визуальное направление:** Generic electronics development/service flow with schematic, board and test-point geometry.
**Создано / обновлено:** 2026-09-23 10:02:18.463532+00 / 2026-09-23 10:02:33.245254+00

Компоненты оценки:
- **buyer_desire**: 8.36 (confidence 0.660). Provisional Forge challenger-concept score derived from occupationally grounded concept archetype plus the fully scored niche prior. It is a research-priority score, not a sales forecast or legal clearance. Дата: 2026-09-23 10:02:33.245254+00.
- **clarity_at_glance**: 9.20 (confidence 0.660). Provisional Forge challenger-concept score derived from occupationally grounded concept archetype plus the fully scored niche prior. It is a research-priority score, not a sales forecast or legal clearance. Дата: 2026-09-23 10:02:33.245254+00.
- **distinctiveness**: 8.50 (confidence 0.660). Provisional Forge challenger-concept score derived from occupationally grounded concept archetype plus the fully scored niche prior. It is a research-priority score, not a sales forecast or legal clearance. Дата: 2026-09-23 10:02:33.245254+00.
- **giftability**: 8.10 (confidence 0.660). Provisional Forge challenger-concept score derived from occupationally grounded concept archetype plus the fully scored niche prior. It is a research-priority score, not a sales forecast or legal clearance. Дата: 2026-09-23 10:02:33.245254+00.
- **insider_resonance**: 8.85 (confidence 0.690). Provisional Forge challenger-concept score derived from occupationally grounded concept archetype plus the fully scored niche prior. It is a research-priority score, not a sales forecast or legal clearance. Дата: 2026-09-23 10:02:33.245254+00.
- **ip_safety**: 9.00 (confidence 0.660). Provisional Forge challenger-concept score derived from occupationally grounded concept archetype plus the fully scored niche prior. It is a research-priority score, not a sales forecast or legal clearance. Дата: 2026-09-23 10:02:33.245254+00.
- **niche_fit**: 9.25 (confidence 0.690). Provisional Forge challenger-concept score derived from occupationally grounded concept archetype plus the fully scored niche prior. It is a research-priority score, not a sales forecast or legal clearance. Дата: 2026-09-23 10:02:33.245254+00.
- **visual_potential**: 8.45 (confidence 0.690). Provisional Forge challenger-concept score derived from occupationally grounded concept archetype plus the fully scored niche prior. It is a research-priority score, not a sales forecast or legal clearance. Дата: 2026-09-23 10:02:33.245254+00.

#### Electronics Tech — schematic to signal path
`eet_schematic_board_signal_path` · ID `f97d8d81-ae7f-4c6e-a70a-2c28b99ac386`

**Интерпретация:** Исторический: снят после owner review; не возвращать автоматически
**Статус БД:** scored · **балл:** 89.52 · **confidence:** 71.06 · **coverage:** 100.00
**Текст / хук:** SCHEMATIC → BOARD → SIGNAL
**Идея:** SCHEMATIC → BOARD → SIGNAL as an original schematic-to-board signal-flow graphic with generic components and test points.
**Покупатель:** Electrical and electronic engineering technologists and technicians
**Причина покупки:** Strong insider technical map and visual differentiation.
**Отличие:** Technical signal-flow language instead of generic circuit-board decoration.
**Визуальное направление:** Original schematic-to-board signal map.
**retired_reason:** failed purchase-trigger quality bar after owner review
**Создано / обновлено:** 2026-09-23 09:59:11.838032+00 / 2026-09-23 23:40:31.847823+00

Компоненты оценки:
- **buyer_desire**: 8.42 (confidence 0.708). Unified Forge diversity-v3 concept score grounded in current occupational tasks and niche evidence. No visual generated; phrase/IP review remains separate. Дата: 2026-09-23 09:59:11.838032+00.
- **clarity_at_glance**: 7.90 (confidence 0.678). Unified Forge diversity-v3 concept score grounded in current occupational tasks and niche evidence. No visual generated; phrase/IP review remains separate. Дата: 2026-09-23 09:59:11.838032+00.
- **distinctiveness**: 9.40 (confidence 0.723). Unified Forge diversity-v3 concept score grounded in current occupational tasks and niche evidence. No visual generated; phrase/IP review remains separate. Дата: 2026-09-23 09:59:11.838032+00.
- **giftability**: 7.42 (confidence 0.663). Unified Forge diversity-v3 concept score grounded in current occupational tasks and niche evidence. No visual generated; phrase/IP review remains separate. Дата: 2026-09-23 09:59:11.838032+00.
- **insider_resonance**: 9.40 (confidence 0.738). Unified Forge diversity-v3 concept score grounded in current occupational tasks and niche evidence. No visual generated; phrase/IP review remains separate. Дата: 2026-09-23 09:59:11.838032+00.
- **ip_safety**: 8.90 (confidence 0.550). Unified Forge diversity-v3 concept score grounded in current occupational tasks and niche evidence. No visual generated; phrase/IP review remains separate. Дата: 2026-09-23 09:59:11.838032+00.
- **niche_fit**: 9.62 (confidence 0.738). Unified Forge diversity-v3 concept score grounded in current occupational tasks and niche evidence. No visual generated; phrase/IP review remains separate. Дата: 2026-09-23 09:59:11.838032+00.
- **visual_potential**: 9.80 (confidence 0.753). Unified Forge diversity-v3 concept score grounded in current occupational tasks and niche evidence. No visual generated; phrase/IP review remains separate. Дата: 2026-09-23 09:59:11.838032+00.

#### Electronics Tech — V / I / signal / frequency
`eet_voltage_current_signal_frequency` · ID `901eaf72-6471-4a9f-8b64-3154d16524b4`

**Интерпретация:** Исследовательский кандидат; одобрение владельца не зафиксировано
**Статус БД:** scored · **балл:** 87.88 · **confidence:** 69.96 · **coverage:** 100.00
**Текст / хук:** VOLTAGE • CURRENT • SIGNAL • FREQUENCY
**Идея:** VOLTAGE • CURRENT • SIGNAL • FREQUENCY as four diagnostic domains around an original meter/waveform composition.
**Покупатель:** Electrical and electronic engineering technologists and technicians
**Причина покупки:** Compact technical vocabulary recognizable to electronics technicians.
**Отличие:** Terminology-led identity rather than generic circuit art.
**Визуальное направление:** Meter/waveform four-domain composition.
**Создано / обновлено:** 2026-09-23 09:59:11.838032+00 / 2026-09-23 09:59:11.838032+00

Компоненты оценки:
- **buyer_desire**: 8.72 (confidence 0.708). Unified Forge diversity-v3 concept score grounded in current occupational tasks and niche evidence. No visual generated; phrase/IP review remains separate. Дата: 2026-09-23 09:59:11.838032+00.
- **clarity_at_glance**: 9.30 (confidence 0.738). Unified Forge diversity-v3 concept score grounded in current occupational tasks and niche evidence. No visual generated; phrase/IP review remains separate. Дата: 2026-09-23 09:59:11.838032+00.
- **distinctiveness**: 8.40 (confidence 0.678). Unified Forge diversity-v3 concept score grounded in current occupational tasks and niche evidence. No visual generated; phrase/IP review remains separate. Дата: 2026-09-23 09:59:11.838032+00.
- **giftability**: 8.62 (confidence 0.701). Unified Forge diversity-v3 concept score grounded in current occupational tasks and niche evidence. No visual generated; phrase/IP review remains separate. Дата: 2026-09-23 09:59:11.838032+00.
- **insider_resonance**: 9.50 (confidence 0.753). Unified Forge diversity-v3 concept score grounded in current occupational tasks and niche evidence. No visual generated; phrase/IP review remains separate. Дата: 2026-09-23 09:59:11.838032+00.
- **ip_safety**: 8.00 (confidence 0.500). Unified Forge diversity-v3 concept score grounded in current occupational tasks and niche evidence. No visual generated; phrase/IP review remains separate. Дата: 2026-09-23 09:59:11.838032+00.
- **niche_fit**: 9.72 (confidence 0.761). Unified Forge diversity-v3 concept score grounded in current occupational tasks and niche evidence. No visual generated; phrase/IP review remains separate. Дата: 2026-09-23 09:59:11.838032+00.
- **visual_potential**: 8.10 (confidence 0.663). Unified Forge diversity-v3 concept score grounded in current occupational tasks and niche evidence. No visual generated; phrase/IP review remains separate. Дата: 2026-09-23 09:59:11.838032+00.

#### Electronics tech — another ruined aha moment
`v4_elec_aha_ruined` · ID `4105989d-85e2-451a-9385-46d82976ff00`

**Интерпретация:** V4: понижен редакционным отбором, сохранен в истории
**Статус БД:** scored · **балл:** 88.77 · **confidence:** 70.32 · **coverage:** 100.00
**Текст / хук:** ANOTHER BEAUTIFUL THEORY. RUINED BY THE BOARD.
**Идея:** Troubleshooting humor about each promising theory failing on the bench.
**Покупатель:** Electrical/electronic engineering technicians and repair techs
**Причина покупки:** Self-deprecating humor with a clear maker/repair audience.
**Отличие:** The punchline is the emotional cycle of troubleshooting.
**Визуальное направление:** Lightbulb/aha icon being crossed out by a stubborn PCB.
**editorial_reason:** structure too close to established beautiful-theory/ugly-fact aphorism
**Создано / обновлено:** 2026-09-23 19:58:09.189566+00 / 2026-09-24 05:05:38.621539+00

Компоненты оценки:
- **buyer_desire**: 8.80 (confidence 0.700). purchase_trigger_v2 preliminary score; gate passed; trigger=self_deprecating_humor Дата: 2026-09-23 19:59:53.152527+00.
- **clarity_at_glance**: 9.20 (confidence 0.760). purchase_trigger_v2 preliminary score; gate passed; trigger=self_deprecating_humor Дата: 2026-09-23 19:59:53.152527+00.
- **distinctiveness**: 8.80 (confidence 0.700). purchase_trigger_v2 preliminary score; gate passed; trigger=self_deprecating_humor Дата: 2026-09-23 19:59:53.152527+00.
- **giftability**: 8.80 (confidence 0.670). purchase_trigger_v2 preliminary score; gate passed; trigger=self_deprecating_humor Дата: 2026-09-23 19:59:53.152527+00.
- **insider_resonance**: 9.00 (confidence 0.720). purchase_trigger_v2 preliminary score; gate passed; trigger=self_deprecating_humor Дата: 2026-09-23 19:59:53.152527+00.
- **ip_safety**: 8.90 (confidence 0.600). purchase_trigger_v2 preliminary score; gate passed; trigger=self_deprecating_humor Дата: 2026-09-23 19:59:53.152527+00.
- **niche_fit**: 9.00 (confidence 0.720). purchase_trigger_v2 preliminary score; gate passed; trigger=self_deprecating_humor Дата: 2026-09-23 19:59:53.152527+00.
- **visual_potential**: 8.80 (confidence 0.720). purchase_trigger_v2 preliminary score; gate passed; trigger=self_deprecating_humor Дата: 2026-09-23 19:59:53.152527+00.

#### Electronics tech — arguing with circuits
`v4_elec_argue_circuit` · ID `374a085a-fe57-4ca2-8172-a49c8cbd45cf`

**Интерпретация:** V4: редакционный финалист на выбор владельца, НЕ подтвержденное одобрение
**Статус БД:** shortlisted · **балл:** 89.25 · **confidence:** 70.32 · **coverage:** 100.00
**Текст / хук:** I ARGUE WITH CIRCUITS UNTIL THEY ADMIT WHAT'S WRONG.
**Идея:** Anthropomorphize diagnosis as an argument with a stubborn board.
**Покупатель:** Electrical/electronic engineering technicians and repair techs
**Причина покупки:** Humor + competence pride; strong visual and gifting potential.
**Отличие:** Human metaphor rather than component list.
**Визуальное направление:** Technician speech bubble facing an annoyed circuit board character.
**Смысл для владельца (источник, EN):** The circuit cannot talk. “Arguing” means repeatedly testing hypotheses until the measurements finally reveal the actual fault.
**Почему это шутка (источник, EN):** Anyone who troubleshoots stubborn electronics knows the feeling of negotiating with a machine that refuses to tell you what is wrong. The phrase turns diagnostic persistence into a human argument.
**Создано / обновлено:** 2026-09-23 19:58:09.189566+00 / 2026-09-24 22:40:42.70901+00

Компоненты оценки:
- **buyer_desire**: 8.80 (confidence 0.700). purchase_trigger_v2 preliminary score; gate passed; trigger=visual_metaphor Дата: 2026-09-23 19:59:53.152527+00.
- **clarity_at_glance**: 8.90 (confidence 0.760). purchase_trigger_v2 preliminary score; gate passed; trigger=visual_metaphor Дата: 2026-09-23 19:59:53.152527+00.
- **distinctiveness**: 9.10 (confidence 0.700). purchase_trigger_v2 preliminary score; gate passed; trigger=visual_metaphor Дата: 2026-09-23 19:59:53.152527+00.
- **giftability**: 8.50 (confidence 0.670). purchase_trigger_v2 preliminary score; gate passed; trigger=visual_metaphor Дата: 2026-09-23 19:59:53.152527+00.
- **insider_resonance**: 8.90 (confidence 0.720). purchase_trigger_v2 preliminary score; gate passed; trigger=visual_metaphor Дата: 2026-09-23 19:59:53.152527+00.
- **ip_safety**: 8.90 (confidence 0.600). purchase_trigger_v2 preliminary score; gate passed; trigger=visual_metaphor Дата: 2026-09-23 19:59:53.152527+00.
- **niche_fit**: 9.00 (confidence 0.720). purchase_trigger_v2 preliminary score; gate passed; trigger=visual_metaphor Дата: 2026-09-23 19:59:53.152527+00.
- **visual_potential**: 9.40 (confidence 0.720). purchase_trigger_v2 preliminary score; gate passed; trigger=visual_metaphor Дата: 2026-09-23 19:59:53.152527+00.

#### Electronics tech — no documentation challenge
`v4_elec_no_datasheet` · ID `6fc3affc-9455-4f7f-978a-deba52820098`

**Интерпретация:** Исследовательский кандидат; одобрение владельца не зафиксировано
**Статус БД:** scored · **балл:** 84.49 · **confidence:** 70.32 · **coverage:** 100.00
**Текст / хук:** NO DATASHEET. NO KNOWN-GOOD SPARE. FINE.
**Идея:** Pride in troubleshooting when documentation and known-good parts are missing.
**Покупатель:** Electrical/electronic engineering technicians and repair techs
**Причина покупки:** Defiant competence/status with real-world specificity.
**Отличие:** A human challenge statement, not terminology salad.
**Визуальное направление:** Blank datasheet page / mystery IC / calm probe in foreground.
**Создано / обновлено:** 2026-09-23 19:58:09.189566+00 / 2026-09-24 05:05:38.621539+00

Компоненты оценки:
- **buyer_desire**: 8.30 (confidence 0.700). purchase_trigger_v2 preliminary score; gate passed; trigger=competence_pride Дата: 2026-09-23 19:59:53.152527+00.
- **clarity_at_glance**: 8.80 (confidence 0.760). purchase_trigger_v2 preliminary score; gate passed; trigger=competence_pride Дата: 2026-09-23 19:59:53.152527+00.
- **distinctiveness**: 8.20 (confidence 0.700). purchase_trigger_v2 preliminary score; gate passed; trigger=competence_pride Дата: 2026-09-23 19:59:53.152527+00.
- **giftability**: 8.00 (confidence 0.670). purchase_trigger_v2 preliminary score; gate passed; trigger=competence_pride Дата: 2026-09-23 19:59:53.152527+00.
- **insider_resonance**: 8.70 (confidence 0.720). purchase_trigger_v2 preliminary score; gate passed; trigger=competence_pride Дата: 2026-09-23 19:59:53.152527+00.
- **ip_safety**: 8.90 (confidence 0.600). purchase_trigger_v2 preliminary score; gate passed; trigger=competence_pride Дата: 2026-09-23 19:59:53.152527+00.
- **niche_fit**: 9.10 (confidence 0.720). purchase_trigger_v2 preliminary score; gate passed; trigger=competence_pride Дата: 2026-09-23 19:59:53.152527+00.
- **visual_potential**: 8.50 (confidence 0.720). purchase_trigger_v2 preliminary score; gate passed; trigger=competence_pride Дата: 2026-09-23 19:59:53.152527+00.

#### Electronics tech — repair versus replace
`v4_elec_replace_vs_fix` · ID `7fcc12b4-83ce-4c21-8757-a644204e337d`

**Интерпретация:** Исследовательский кандидат; одобрение владельца не зафиксировано
**Статус БД:** scored · **балл:** 88.01 · **confidence:** 70.32 · **coverage:** 100.00
**Текст / хук:** EVERYONE ELSE REPLACES THE BOARD. I WANT TO KNOW WHY.
**Идея:** Identity concept for people who want to know why the board failed instead of swapping it.
**Покупатель:** Electrical/electronic engineering technicians and repair techs
**Причина покупки:** Strong repair-craft identity and anti-disposability pride.
**Отличие:** The differentiation is curiosity/craft, not a list of repair skills.
**Визуальное направление:** Trash-bin arrow versus microscope/probe path into board.
**Создано / обновлено:** 2026-09-23 19:58:09.189566+00 / 2026-09-24 05:05:38.621539+00

Компоненты оценки:
- **buyer_desire**: 8.70 (confidence 0.700). purchase_trigger_v2 preliminary score; gate passed; trigger=craft_pride Дата: 2026-09-23 19:59:53.152527+00.
- **clarity_at_glance**: 9.00 (confidence 0.760). purchase_trigger_v2 preliminary score; gate passed; trigger=craft_pride Дата: 2026-09-23 19:59:53.152527+00.
- **distinctiveness**: 8.70 (confidence 0.700). purchase_trigger_v2 preliminary score; gate passed; trigger=craft_pride Дата: 2026-09-23 19:59:53.152527+00.
- **giftability**: 8.50 (confidence 0.670). purchase_trigger_v2 preliminary score; gate passed; trigger=craft_pride Дата: 2026-09-23 19:59:53.152527+00.
- **insider_resonance**: 9.00 (confidence 0.720). purchase_trigger_v2 preliminary score; gate passed; trigger=craft_pride Дата: 2026-09-23 19:59:53.152527+00.
- **ip_safety**: 8.90 (confidence 0.600). purchase_trigger_v2 preliminary score; gate passed; trigger=craft_pride Дата: 2026-09-23 19:59:53.152527+00.
- **niche_fit**: 9.30 (confidence 0.720). purchase_trigger_v2 preliminary score; gate passed; trigger=craft_pride Дата: 2026-09-23 19:59:53.152527+00.
- **visual_potential**: 8.80 (confidence 0.720). purchase_trigger_v2 preliminary score; gate passed; trigger=craft_pride Дата: 2026-09-23 19:59:53.152527+00.

#### Electronics tech — schematic optimism
`v4_elec_schematic_should` · ID `244b7389-88dc-4a51-a6b6-280924830e2d`

**Интерпретация:** V4: понижен редакционным отбором, сохранен в истории
**Статус БД:** scored · **балл:** 90.58 · **confidence:** 70.32 · **coverage:** 100.00
**Текст / хук:** THE SCHEMATIC SAYS IT SHOULD WORK.
**Идея:** The schematic claims the board should work; reality disagrees.
**Покупатель:** Electrical/electronic engineering technicians and repair techs
**Причина покупки:** Universal technician frustration with strong insider recognition.
**Отличие:** The joke is model-versus-reality, not component vocabulary.
**Визуальное направление:** Clean schematic on left, chaotic stubborn board on right.
**editorial_reason:** generic technical phrasing found in prior technical prose
**Создано / обновлено:** 2026-09-23 19:58:09.189566+00 / 2026-09-24 05:05:38.621539+00

Компоненты оценки:
- **buyer_desire**: 9.10 (confidence 0.700). purchase_trigger_v2 preliminary score; gate passed; trigger=troubleshooting_humor Дата: 2026-09-23 19:59:53.152527+00.
- **clarity_at_glance**: 9.40 (confidence 0.760). purchase_trigger_v2 preliminary score; gate passed; trigger=troubleshooting_humor Дата: 2026-09-23 19:59:53.152527+00.
- **distinctiveness**: 8.90 (confidence 0.700). purchase_trigger_v2 preliminary score; gate passed; trigger=troubleshooting_humor Дата: 2026-09-23 19:59:53.152527+00.
- **giftability**: 8.80 (confidence 0.670). purchase_trigger_v2 preliminary score; gate passed; trigger=troubleshooting_humor Дата: 2026-09-23 19:59:53.152527+00.
- **insider_resonance**: 9.30 (confidence 0.720). purchase_trigger_v2 preliminary score; gate passed; trigger=troubleshooting_humor Дата: 2026-09-23 19:59:53.152527+00.
- **ip_safety**: 8.90 (confidence 0.600). purchase_trigger_v2 preliminary score; gate passed; trigger=troubleshooting_humor Дата: 2026-09-23 19:59:53.152527+00.
- **niche_fit**: 9.30 (confidence 0.720). purchase_trigger_v2 preliminary score; gate passed; trigger=troubleshooting_humor Дата: 2026-09-23 19:59:53.152527+00.
- **visual_potential**: 8.80 (confidence 0.720). purchase_trigger_v2 preliminary score; gate passed; trigger=troubleshooting_humor Дата: 2026-09-23 19:59:53.152527+00.

## 15. Elevator & Escalator Mechanic
Ключ: `elevator_mechanic` · ID: `24a8b363-f1b4-4b82-8394-dbf150e1dcf4`

**Статус БД:** scored · **балл:** 77.85 · **confidence:** 70.80 · **coverage:** 100.00
**Аудитория:** Elevator and escalator installers, repairers, apprentices and service crews
**Категория:** occupational_identity
**Исследовательская аргументация:** Small, high-skill trade with strong insider identity, high pay, distinctive machinery/shaft/control-panel visual language, and sampled merch that is present but not lineman-scale.
**Создано / обновлено:** 2026-09-23 09:34:00.70472+00 / 2026-09-23 09:34:30.438105+00

### Компоненты оценки ниши

- **channel_breadth**: 7.00 (confidence 0.550). Initial evidence-weighted Forge score from current BLS/O*NET data, sampled Etsy competition and practitioner-community signals. See niche_candidates.source_notes. This is prioritization research, not a sales forecast. Дата: 2026-09-23 09:34:30.438105+00.
- **competition_opportunity**: 7.00 (confidence 0.600). Initial evidence-weighted Forge score from current BLS/O*NET data, sampled Etsy competition and practitioner-community signals. See niche_candidates.source_notes. This is prioritization research, not a sales forecast. Дата: 2026-09-23 09:34:30.438105+00.
- **concept_depth**: 9.00 (confidence 0.750). Initial evidence-weighted Forge score from current BLS/O*NET data, sampled Etsy competition and practitioner-community signals. See niche_candidates.source_notes. This is prioritization research, not a sales forecast. Дата: 2026-09-23 09:34:30.438105+00.
- **demand_evidence**: 7.20 (confidence 0.800). Initial evidence-weighted Forge score from current BLS/O*NET data, sampled Etsy competition and practitioner-community signals. See niche_candidates.source_notes. This is prioritization research, not a sales forecast. Дата: 2026-09-23 09:34:30.438105+00.
- **founder_edge**: 2.00 (confidence 0.400). Initial evidence-weighted Forge score from current BLS/O*NET data, sampled Etsy competition and practitioner-community signals. See niche_candidates.source_notes. This is prioritization research, not a sales forecast. Дата: 2026-09-23 09:34:30.438105+00.
- **identity_intensity**: 8.50 (confidence 0.750). Initial evidence-weighted Forge score from current BLS/O*NET data, sampled Etsy competition and practitioner-community signals. See niche_candidates.source_notes. This is prioritization research, not a sales forecast. Дата: 2026-09-23 09:34:30.438105+00.
- **legal_safety**: 8.50 (confidence 0.700). Initial evidence-weighted Forge score from current BLS/O*NET data, sampled Etsy competition and practitioner-community signals. See niche_candidates.source_notes. This is prioritization research, not a sales forecast. Дата: 2026-09-23 09:34:30.438105+00.
- **purchase_motivation**: 8.00 (confidence 0.700). Initial evidence-weighted Forge score from current BLS/O*NET data, sampled Etsy competition and practitioner-community signals. See niche_candidates.source_notes. This is prioritization research, not a sales forecast. Дата: 2026-09-23 09:34:30.438105+00.
- **repeatability**: 7.50 (confidence 0.600). Initial evidence-weighted Forge score from current BLS/O*NET data, sampled Etsy competition and practitioner-community signals. See niche_candidates.source_notes. This is prioritization research, not a sales forecast. Дата: 2026-09-23 09:34:30.438105+00.
- **visual_language**: 9.00 (confidence 0.800). Initial evidence-weighted Forge score from current BLS/O*NET data, sampled Etsy competition and practitioner-community signals. See niche_candidates.source_notes. This is prioritization research, not a sales forecast. Дата: 2026-09-23 09:34:30.438105+00.

### Концепции (3)

#### Elevator Mechanic — system stack
`elevator_drive_brake_door_control` · ID `39f0bb68-9d9b-46a8-a885-e63d2e0579e2`

**Интерпретация:** Исследовательский кандидат; одобрение владельца не зафиксировано
**Статус БД:** scored · **балл:** 89.29 · **confidence:** 71.68 · **coverage:** 100.00
**Текст / хук:** DRIVE • BRAKE • DOOR • CONTROL
**Идея:** ELEVATOR MECHANIC / VERTICAL TRANSPORT system graphic organized around DRIVE • BRAKE • DOOR • CONTROL, with an original abstract machine-room/hoistway schematic. Avoid manufacturer names and proprietary controller layouts.
**Покупатель:** Elevator and escalator installers and repairers
**Причина покупки:** Makes the complex multi-system nature of the trade visible.
**Отличие:** Technical system identity stands apart from sampled up/down jokes and generic mechanic art.
**Визуальное направление:** Vertical schematic with car, sheave/drive, door zone and controller blocks
**Создано / обновлено:** 2026-09-23 09:36:02.928333+00 / 2026-09-23 10:15:01.390702+00

Компоненты оценки:
- **buyer_desire**: 8.50 (confidence 0.680). Initial Forge concept score using current occupational terminology, sampled marketplace patterns and technical distinctiveness. No visual has been generated; exact phrases still require IP/common-law screening before promotion. Дата: 2026-09-23 09:36:38.256823+00.
- **clarity_at_glance**: 8.50 (confidence 0.680). Initial Forge concept score using current occupational terminology, sampled marketplace patterns and technical distinctiveness. No visual has been generated; exact phrases still require IP/common-law screening before promotion. Дата: 2026-09-23 09:36:38.256823+00.
- **distinctiveness**: 9.30 (confidence 0.720). Initial Forge concept score using current occupational terminology, sampled marketplace patterns and technical distinctiveness. No visual has been generated; exact phrases still require IP/common-law screening before promotion. Дата: 2026-09-23 09:36:38.256823+00.
- **giftability**: 8.00 (confidence 0.640). Initial Forge concept score using current occupational terminology, sampled marketplace patterns and technical distinctiveness. No visual has been generated; exact phrases still require IP/common-law screening before promotion. Дата: 2026-09-23 09:36:38.256823+00.
- **insider_resonance**: 9.00 (confidence 0.740). Initial Forge concept score using current occupational terminology, sampled marketplace patterns and technical distinctiveness. No visual has been generated; exact phrases still require IP/common-law screening before promotion. Дата: 2026-09-23 09:36:38.256823+00.
- **ip_safety**: 9.00 (confidence 0.700). Initial Forge concept score using current occupational terminology, sampled marketplace patterns and technical distinctiveness. No visual has been generated; exact phrases still require IP/common-law screening before promotion. Дата: 2026-09-23 09:36:38.256823+00.
- **niche_fit**: 9.50 (confidence 0.780). Initial Forge concept score using current occupational terminology, sampled marketplace patterns and technical distinctiveness. No visual has been generated; exact phrases still require IP/common-law screening before promotion. Дата: 2026-09-23 09:36:38.256823+00.
- **visual_potential**: 9.50 (confidence 0.780). Initial Forge concept score using current occupational terminology, sampled marketplace patterns and technical distinctiveness. No visual has been generated; exact phrases still require IP/common-law screening before promotion. Дата: 2026-09-23 09:36:38.256823+00.

#### Elevator Mechanic — hoistway / machine room / controller
`elevator_hoistway_machine_room_controller` · ID `27362360-5c6a-48b9-b535-149a7095cd7f`

**Интерпретация:** Исследовательский кандидат; одобрение владельца не зафиксировано
**Статус БД:** scored · **балл:** 87.35 · **confidence:** 68.80 · **coverage:** 100.00
**Текст / хук:** HOISTWAY • MACHINE ROOM • CONTROLLER
**Идея:** ELEVATOR MECHANIC composition connecting HOISTWAY • MACHINE ROOM • CONTROLLER as the three major spaces/systems of service work, rendered as an original sectional diagram rather than a real manufacturer drawing.
**Покупатель:** Elevator mechanics and lift technicians
**Причина покупки:** Strong trade-specific vocabulary that reads as insider knowledge.
**Отличие:** Architectural/service-system diagram instead of elevator-button novelty.
**Визуальное направление:** Tall sectional cutaway with simplified controller, machine and car/rail geometry
**Создано / обновлено:** 2026-09-23 09:36:02.928333+00 / 2026-09-23 10:09:42.905504+00

Компоненты оценки:
- **buyer_desire**: 8.00 (confidence 0.620). Initial Forge concept score using current occupational terminology, sampled marketplace patterns and technical distinctiveness. No visual has been generated; exact phrases still require IP/common-law screening before promotion. Дата: 2026-09-23 09:36:38.256823+00.
- **clarity_at_glance**: 7.50 (confidence 0.580). Initial Forge concept score using current occupational terminology, sampled marketplace patterns and technical distinctiveness. No visual has been generated; exact phrases still require IP/common-law screening before promotion. Дата: 2026-09-23 09:36:38.256823+00.
- **distinctiveness**: 9.00 (confidence 0.700). Initial Forge concept score using current occupational terminology, sampled marketplace patterns and technical distinctiveness. No visual has been generated; exact phrases still require IP/common-law screening before promotion. Дата: 2026-09-23 09:36:38.256823+00.
- **giftability**: 7.50 (confidence 0.580). Initial Forge concept score using current occupational terminology, sampled marketplace patterns and technical distinctiveness. No visual has been generated; exact phrases still require IP/common-law screening before promotion. Дата: 2026-09-23 09:36:38.256823+00.
- **insider_resonance**: 9.50 (confidence 0.760). Initial Forge concept score using current occupational terminology, sampled marketplace patterns and technical distinctiveness. No visual has been generated; exact phrases still require IP/common-law screening before promotion. Дата: 2026-09-23 09:36:38.256823+00.
- **ip_safety**: 9.00 (confidence 0.700). Initial Forge concept score using current occupational terminology, sampled marketplace patterns and technical distinctiveness. No visual has been generated; exact phrases still require IP/common-law screening before promotion. Дата: 2026-09-23 09:36:38.256823+00.
- **niche_fit**: 9.50 (confidence 0.780). Initial Forge concept score using current occupational terminology, sampled marketplace patterns and technical distinctiveness. No visual has been generated; exact phrases still require IP/common-law screening before promotion. Дата: 2026-09-23 09:36:38.256823+00.
- **visual_potential**: 9.50 (confidence 0.760). Initial Forge concept score using current occupational terminology, sampled marketplace patterns and technical distinctiveness. No visual has been generated; exact phrases still require IP/common-law screening before promotion. Дата: 2026-09-23 09:36:38.256823+00.

#### Elevator Mechanic — service loop
`elevator_inspect_test_adjust_repair` · ID `2fa4285d-0546-49c6-8b4a-80a5c8323cea`

**Интерпретация:** Исследовательский кандидат; одобрение владельца не зафиксировано
**Статус БД:** scored · **балл:** 82.31 · **confidence:** 63.96 · **coverage:** 100.00
**Текст / хук:** INSPECT • TEST • ADJUST • REPAIR
**Идея:** ELEVATOR MECHANIC service workflow INSPECT • TEST • ADJUST • REPAIR, paired with original generic lift-system components and test points. Keep it identity-focused, not instructional or safety-procedure content.
**Покупатель:** Elevator mechanics and service technicians
**Причина покупки:** Clear professional identity and broad giftability for service crews/apprentices.
**Отличие:** Cleaner and more credible than generic “I fix things” mechanic slogans.
**Визуальное направление:** Four-step service loop around simplified lift-system line art
**Создано / обновлено:** 2026-09-23 09:36:02.928333+00 / 2026-09-23 10:09:42.905504+00

Компоненты оценки:
- **buyer_desire**: 7.80 (confidence 0.600). Initial Forge concept score using current occupational terminology, sampled marketplace patterns and technical distinctiveness. No visual has been generated; exact phrases still require IP/common-law screening before promotion. Дата: 2026-09-23 09:36:38.256823+00.
- **clarity_at_glance**: 9.00 (confidence 0.720). Initial Forge concept score using current occupational terminology, sampled marketplace patterns and technical distinctiveness. No visual has been generated; exact phrases still require IP/common-law screening before promotion. Дата: 2026-09-23 09:36:38.256823+00.
- **distinctiveness**: 8.00 (confidence 0.600). Initial Forge concept score using current occupational terminology, sampled marketplace patterns and technical distinctiveness. No visual has been generated; exact phrases still require IP/common-law screening before promotion. Дата: 2026-09-23 09:36:38.256823+00.
- **giftability**: 7.50 (confidence 0.580). Initial Forge concept score using current occupational terminology, sampled marketplace patterns and technical distinctiveness. No visual has been generated; exact phrases still require IP/common-law screening before promotion. Дата: 2026-09-23 09:36:38.256823+00.
- **insider_resonance**: 8.50 (confidence 0.680). Initial Forge concept score using current occupational terminology, sampled marketplace patterns and technical distinctiveness. No visual has been generated; exact phrases still require IP/common-law screening before promotion. Дата: 2026-09-23 09:36:38.256823+00.
- **ip_safety**: 9.50 (confidence 0.720). Initial Forge concept score using current occupational terminology, sampled marketplace patterns and technical distinctiveness. No visual has been generated; exact phrases still require IP/common-law screening before promotion. Дата: 2026-09-23 09:36:38.256823+00.
- **niche_fit**: 9.00 (confidence 0.720). Initial Forge concept score using current occupational terminology, sampled marketplace patterns and technical distinctiveness. No visual has been generated; exact phrases still require IP/common-law screening before promotion. Дата: 2026-09-23 09:36:38.256823+00.
- **visual_potential**: 8.00 (confidence 0.620). Initial Forge concept score using current occupational terminology, sampled marketplace patterns and technical distinctiveness. No visual has been generated; exact phrases still require IP/common-law screening before promotion. Дата: 2026-09-23 09:36:38.256823+00.

## 16. Environmental Science & Protection Technician
Ключ: `environmental_science_protection_technician` · ID: `e1b2c74c-ca75-48cc-b7e9-dfb309808b5e`

**Статус БД:** scored · **балл:** 78.25 · **confidence:** 64.62 · **coverage:** 100.00
**Аудитория:** Environmental field, sampling, monitoring and compliance technicians
**Категория:** occupational_identity
**Исследовательская аргументация:** Growing field/lab occupation with authentic identity around sampling, monitoring, field instruments, compliance and pollution control. Sampled exact Etsy search did not surface a dedicated category, suggesting possible whitespace but with lower-confidence market evidence.
**Создано / обновлено:** 2026-09-23 09:56:40.513406+00 / 2026-09-23 09:56:40.513406+00

### Компоненты оценки ниши

- **channel_breadth**: 8.50 (confidence 0.640). Forge diversity-batch v3 score using current 2025-35 BLS/O*NET evidence plus sampled current Etsy competition. Where exact marketplace counts were unavailable, competition confidence is intentionally lower. Дата: 2026-09-23 09:56:40.513406+00.
- **competition_opportunity**: 8.50 (confidence 0.480). Forge diversity-batch v3 score using current 2025-35 BLS/O*NET evidence plus sampled current Etsy competition. Where exact marketplace counts were unavailable, competition confidence is intentionally lower. Дата: 2026-09-23 09:56:40.513406+00.
- **concept_depth**: 8.50 (confidence 0.680). Forge diversity-batch v3 score using current 2025-35 BLS/O*NET evidence plus sampled current Etsy competition. Where exact marketplace counts were unavailable, competition confidence is intentionally lower. Дата: 2026-09-23 09:56:40.513406+00.
- **demand_evidence**: 8.00 (confidence 0.880). Forge diversity-batch v3 score using current 2025-35 BLS/O*NET evidence plus sampled current Etsy competition. Where exact marketplace counts were unavailable, competition confidence is intentionally lower. Дата: 2026-09-23 09:56:40.513406+00.
- **founder_edge**: 2.00 (confidence 0.400). Forge diversity-batch v3 score using current 2025-35 BLS/O*NET evidence plus sampled current Etsy competition. Where exact marketplace counts were unavailable, competition confidence is intentionally lower. Дата: 2026-09-23 09:56:40.513406+00.
- **identity_intensity**: 7.00 (confidence 0.580). Forge diversity-batch v3 score using current 2025-35 BLS/O*NET evidence plus sampled current Etsy competition. Where exact marketplace counts were unavailable, competition confidence is intentionally lower. Дата: 2026-09-23 09:56:40.513406+00.
- **legal_safety**: 9.00 (confidence 0.680). Forge diversity-batch v3 score using current 2025-35 BLS/O*NET evidence plus sampled current Etsy competition. Where exact marketplace counts were unavailable, competition confidence is intentionally lower. Дата: 2026-09-23 09:56:40.513406+00.
- **purchase_motivation**: 7.00 (confidence 0.540). Forge diversity-batch v3 score using current 2025-35 BLS/O*NET evidence plus sampled current Etsy competition. Where exact marketplace counts were unavailable, competition confidence is intentionally lower. Дата: 2026-09-23 09:56:40.513406+00.
- **repeatability**: 7.50 (confidence 0.580). Forge diversity-batch v3 score using current 2025-35 BLS/O*NET evidence plus sampled current Etsy competition. Where exact marketplace counts were unavailable, competition confidence is intentionally lower. Дата: 2026-09-23 09:56:40.513406+00.
- **visual_language**: 9.00 (confidence 0.740). Forge diversity-batch v3 score using current 2025-35 BLS/O*NET evidence plus sampled current Etsy competition. Where exact marketplace counts were unavailable, competition confidence is intentionally lower. Дата: 2026-09-23 09:56:40.513406+00.

### Концепции (0)

## 17. Fire Inspector / Investigator
Ключ: `fire_inspector` · ID: `2fcffef6-c85a-4117-9447-9a78c6e811eb`

**Статус БД:** scored · **балл:** 73.45 · **confidence:** 72.12 · **coverage:** 100.00
**Аудитория:** Fire inspectors, investigators and prevention specialists
**Категория:** occupational_identity
**Исследовательская аргументация:** Real professional identity and code/investigation language, but official-looking seals/department marks create execution constraints and merch demand is not yet proven.
**Создано / обновлено:** 2026-09-23 09:34:00.70472+00 / 2026-09-23 09:57:21.800356+00

### Компоненты оценки ниши

- **channel_breadth**: 7.00 (confidence 0.560). Current BLS shows 17,600 fire inspectors with 6% projected 2025-35 growth and 1,900 annual openings. Sampled Etsy shows multiple dedicated Fire Inspector designs inside broader inspector search; official badge/seal/department visual risk reduces legal-safety score. Дата: 2026-09-23 09:57:21.800356+00.
- **competition_opportunity**: 6.50 (confidence 0.640). Current BLS shows 17,600 fire inspectors with 6% projected 2025-35 growth and 1,900 annual openings. Sampled Etsy shows multiple dedicated Fire Inspector designs inside broader inspector search; official badge/seal/department visual risk reduces legal-safety score. Дата: 2026-09-23 09:57:21.800356+00.
- **concept_depth**: 9.00 (confidence 0.760). Current BLS shows 17,600 fire inspectors with 6% projected 2025-35 growth and 1,900 annual openings. Sampled Etsy shows multiple dedicated Fire Inspector designs inside broader inspector search; official badge/seal/department visual risk reduces legal-safety score. Дата: 2026-09-23 09:57:21.800356+00.
- **demand_evidence**: 6.50 (confidence 0.900). Current BLS shows 17,600 fire inspectors with 6% projected 2025-35 growth and 1,900 annual openings. Sampled Etsy shows multiple dedicated Fire Inspector designs inside broader inspector search; official badge/seal/department visual risk reduces legal-safety score. Дата: 2026-09-23 09:57:21.800356+00.
- **founder_edge**: 2.00 (confidence 0.400). Current BLS shows 17,600 fire inspectors with 6% projected 2025-35 growth and 1,900 annual openings. Sampled Etsy shows multiple dedicated Fire Inspector designs inside broader inspector search; official badge/seal/department visual risk reduces legal-safety score. Дата: 2026-09-23 09:57:21.800356+00.
- **identity_intensity**: 8.00 (confidence 0.720). Current BLS shows 17,600 fire inspectors with 6% projected 2025-35 growth and 1,900 annual openings. Sampled Etsy shows multiple dedicated Fire Inspector designs inside broader inspector search; official badge/seal/department visual risk reduces legal-safety score. Дата: 2026-09-23 09:57:21.800356+00.
- **legal_safety**: 6.00 (confidence 0.720). Current BLS shows 17,600 fire inspectors with 6% projected 2025-35 growth and 1,900 annual openings. Sampled Etsy shows multiple dedicated Fire Inspector designs inside broader inspector search; official badge/seal/department visual risk reduces legal-safety score. Дата: 2026-09-23 09:57:21.800356+00.
- **purchase_motivation**: 7.50 (confidence 0.640). Current BLS shows 17,600 fire inspectors with 6% projected 2025-35 growth and 1,900 annual openings. Sampled Etsy shows multiple dedicated Fire Inspector designs inside broader inspector search; official badge/seal/department visual risk reduces legal-safety score. Дата: 2026-09-23 09:57:21.800356+00.
- **repeatability**: 7.50 (confidence 0.600). Current BLS shows 17,600 fire inspectors with 6% projected 2025-35 growth and 1,900 annual openings. Sampled Etsy shows multiple dedicated Fire Inspector designs inside broader inspector search; official badge/seal/department visual risk reduces legal-safety score. Дата: 2026-09-23 09:57:21.800356+00.
- **visual_language**: 9.00 (confidence 0.780). Current BLS shows 17,600 fire inspectors with 6% projected 2025-35 growth and 1,900 annual openings. Sampled Etsy shows multiple dedicated Fire Inspector designs inside broader inspector search; official badge/seal/department visual risk reduces legal-safety score. Дата: 2026-09-23 09:57:21.800356+00.

### Концепции (0)

## 18. Gas Plant Operator
Ключ: `gas_plant_operator` · ID: `4e052e26-5be1-44ef-8217-c02832c6d3a7`

**Статус БД:** scored · **балл:** 71.85 · **confidence:** 63.92 · **coverage:** 100.00
**Аудитория:** Natural-gas processing plant operators
**Категория:** occupational_identity
**Исследовательская аргументация:** Small high-skill process-operations niche with compression, pressure, flow and control-room language; employment is projected to decline, so this is a concept-quality rather than growth bet.
**Создано / обновлено:** 2026-09-23 10:00:20.805089+00 / 2026-09-23 10:04:52.652496+00

### Компоненты оценки ниши

- **channel_breadth**: 6.50 (confidence 0.500). Forge pool-completion provisional score using current BLS/O*NET evidence and sampled Etsy competition. Lower confidence is intentional where exact employment sizing or clean marketplace decomposition is unavailable. Дата: 2026-09-23 10:04:52.652496+00.
- **competition_opportunity**: 8.00 (confidence 0.480). Forge pool-completion provisional score using current BLS/O*NET evidence and sampled Etsy competition. Lower confidence is intentional where exact employment sizing or clean marketplace decomposition is unavailable. Дата: 2026-09-23 10:04:52.652496+00.
- **concept_depth**: 8.50 (confidence 0.640). Forge pool-completion provisional score using current BLS/O*NET evidence and sampled Etsy competition. Lower confidence is intentional where exact employment sizing or clean marketplace decomposition is unavailable. Дата: 2026-09-23 10:04:52.652496+00.
- **demand_evidence**: 5.20 (confidence 0.900). Forge pool-completion provisional score using current BLS/O*NET evidence and sampled Etsy competition. Lower confidence is intentional where exact employment sizing or clean marketplace decomposition is unavailable. Дата: 2026-09-23 10:04:52.652496+00.
- **founder_edge**: 2.00 (confidence 0.400). Forge pool-completion provisional score using current BLS/O*NET evidence and sampled Etsy competition. Lower confidence is intentional where exact employment sizing or clean marketplace decomposition is unavailable. Дата: 2026-09-23 10:04:52.652496+00.
- **identity_intensity**: 8.00 (confidence 0.620). Forge pool-completion provisional score using current BLS/O*NET evidence and sampled Etsy competition. Lower confidence is intentional where exact employment sizing or clean marketplace decomposition is unavailable. Дата: 2026-09-23 10:04:52.652496+00.
- **legal_safety**: 8.00 (confidence 0.580). Forge pool-completion provisional score using current BLS/O*NET evidence and sampled Etsy competition. Lower confidence is intentional where exact employment sizing or clean marketplace decomposition is unavailable. Дата: 2026-09-23 10:04:52.652496+00.
- **purchase_motivation**: 7.00 (confidence 0.560). Forge pool-completion provisional score using current BLS/O*NET evidence and sampled Etsy competition. Lower confidence is intentional where exact employment sizing or clean marketplace decomposition is unavailable. Дата: 2026-09-23 10:04:52.652496+00.
- **repeatability**: 7.00 (confidence 0.540). Forge pool-completion provisional score using current BLS/O*NET evidence and sampled Etsy competition. Lower confidence is intentional where exact employment sizing or clean marketplace decomposition is unavailable. Дата: 2026-09-23 10:04:52.652496+00.
- **visual_language**: 9.00 (confidence 0.700). Forge pool-completion provisional score using current BLS/O*NET evidence and sampled Etsy competition. Lower confidence is intentional where exact employment sizing or clean marketplace decomposition is unavailable. Дата: 2026-09-23 10:04:52.652496+00.

### Концепции (0)

## 19. Geological / Hydrologic Technician
Ключ: `geological_hydrologic_technician` · ID: `49679cdd-e2de-4618-b796-76f838caa476`

**Статус БД:** scored · **балл:** 76.25 · **confidence:** 66.82 · **coverage:** 100.00
**Аудитория:** Geological, hydrologic and field data technicians
**Категория:** occupational_identity
**Исследовательская аргументация:** Small field-science niche with unusually strong visual language around cores, samples, water levels, maps, field instruments and remote-site data collection. Low raw employment but potentially strong insider identity and marketplace whitespace.
**Создано / обновлено:** 2026-09-23 09:56:40.513406+00 / 2026-09-23 09:56:40.513406+00

### Компоненты оценки ниши

- **channel_breadth**: 8.00 (confidence 0.600). Forge diversity-batch v3 score using current 2025-35 BLS/O*NET evidence plus sampled current Etsy competition. Where exact marketplace counts were unavailable, competition confidence is intentionally lower. Дата: 2026-09-23 09:56:40.513406+00.
- **competition_opportunity**: 9.00 (confidence 0.460). Forge diversity-batch v3 score using current 2025-35 BLS/O*NET evidence plus sampled current Etsy competition. Where exact marketplace counts were unavailable, competition confidence is intentionally lower. Дата: 2026-09-23 09:56:40.513406+00.
- **concept_depth**: 9.00 (confidence 0.720). Forge diversity-batch v3 score using current 2025-35 BLS/O*NET evidence plus sampled current Etsy competition. Where exact marketplace counts were unavailable, competition confidence is intentionally lower. Дата: 2026-09-23 09:56:40.513406+00.
- **demand_evidence**: 5.50 (confidence 0.900). Forge diversity-batch v3 score using current 2025-35 BLS/O*NET evidence plus sampled current Etsy competition. Where exact marketplace counts were unavailable, competition confidence is intentionally lower. Дата: 2026-09-23 09:56:40.513406+00.
- **founder_edge**: 2.00 (confidence 0.400). Forge diversity-batch v3 score using current 2025-35 BLS/O*NET evidence plus sampled current Etsy competition. Where exact marketplace counts were unavailable, competition confidence is intentionally lower. Дата: 2026-09-23 09:56:40.513406+00.
- **identity_intensity**: 8.00 (confidence 0.660). Forge diversity-batch v3 score using current 2025-35 BLS/O*NET evidence plus sampled current Etsy competition. Where exact marketplace counts were unavailable, competition confidence is intentionally lower. Дата: 2026-09-23 09:56:40.513406+00.
- **legal_safety**: 9.00 (confidence 0.680). Forge diversity-batch v3 score using current 2025-35 BLS/O*NET evidence plus sampled current Etsy competition. Where exact marketplace counts were unavailable, competition confidence is intentionally lower. Дата: 2026-09-23 09:56:40.513406+00.
- **purchase_motivation**: 7.00 (confidence 0.560). Forge diversity-batch v3 score using current 2025-35 BLS/O*NET evidence plus sampled current Etsy competition. Where exact marketplace counts were unavailable, competition confidence is intentionally lower. Дата: 2026-09-23 09:56:40.513406+00.
- **repeatability**: 7.50 (confidence 0.580). Forge diversity-batch v3 score using current 2025-35 BLS/O*NET evidence plus sampled current Etsy competition. Where exact marketplace counts were unavailable, competition confidence is intentionally lower. Дата: 2026-09-23 09:56:40.513406+00.
- **visual_language**: 9.50 (confidence 0.780). Forge diversity-batch v3 score using current 2025-35 BLS/O*NET evidence plus sampled current Etsy competition. Where exact marketplace counts were unavailable, competition confidence is intentionally lower. Дата: 2026-09-23 09:56:40.513406+00.

### Концепции (0)

## 20. Hearing Aid Specialist
Ключ: `hearing_aid_specialist` · ID: `3b25ea72-c1c4-4e5a-bf45-0f79c7bae7b2`

**Статус БД:** scored · **балл:** 72.30 · **confidence:** 67.32 · **coverage:** 100.00
**Аудитория:** Hearing aid / hearing instrument specialists
**Категория:** occupational_identity
**Исследовательская аргументация:** Small but fast-growing hearing-care occupation with fitting/programming/device visual language. Dedicated merch exists but is still relatively bounded at 43+ sampled Etsy items, much of it generic definition/audiology crossover.
**Создано / обновлено:** 2026-09-23 10:00:20.805089+00 / 2026-09-23 10:04:52.652496+00

### Компоненты оценки ниши

- **channel_breadth**: 7.50 (confidence 0.560). Forge pool-completion provisional score using current BLS/O*NET evidence and sampled Etsy competition. Lower confidence is intentional where exact employment sizing or clean marketplace decomposition is unavailable. Дата: 2026-09-23 10:04:52.652496+00.
- **competition_opportunity**: 6.50 (confidence 0.800). Forge pool-completion provisional score using current BLS/O*NET evidence and sampled Etsy competition. Lower confidence is intentional where exact employment sizing or clean marketplace decomposition is unavailable. Дата: 2026-09-23 10:04:52.652496+00.
- **concept_depth**: 8.50 (confidence 0.660). Forge pool-completion provisional score using current BLS/O*NET evidence and sampled Etsy competition. Lower confidence is intentional where exact employment sizing or clean marketplace decomposition is unavailable. Дата: 2026-09-23 10:04:52.652496+00.
- **demand_evidence**: 6.50 (confidence 0.760). Forge pool-completion provisional score using current BLS/O*NET evidence and sampled Etsy competition. Lower confidence is intentional where exact employment sizing or clean marketplace decomposition is unavailable. Дата: 2026-09-23 10:04:52.652496+00.
- **founder_edge**: 2.00 (confidence 0.400). Forge pool-completion provisional score using current BLS/O*NET evidence and sampled Etsy competition. Lower confidence is intentional where exact employment sizing or clean marketplace decomposition is unavailable. Дата: 2026-09-23 10:04:52.652496+00.
- **identity_intensity**: 7.50 (confidence 0.620). Forge pool-completion provisional score using current BLS/O*NET evidence and sampled Etsy competition. Lower confidence is intentional where exact employment sizing or clean marketplace decomposition is unavailable. Дата: 2026-09-23 10:04:52.652496+00.
- **legal_safety**: 7.50 (confidence 0.580). Forge pool-completion provisional score using current BLS/O*NET evidence and sampled Etsy competition. Lower confidence is intentional where exact employment sizing or clean marketplace decomposition is unavailable. Дата: 2026-09-23 10:04:52.652496+00.
- **purchase_motivation**: 7.00 (confidence 0.580). Forge pool-completion provisional score using current BLS/O*NET evidence and sampled Etsy competition. Lower confidence is intentional where exact employment sizing or clean marketplace decomposition is unavailable. Дата: 2026-09-23 10:04:52.652496+00.
- **repeatability**: 8.00 (confidence 0.620). Forge pool-completion provisional score using current BLS/O*NET evidence and sampled Etsy competition. Lower confidence is intentional where exact employment sizing or clean marketplace decomposition is unavailable. Дата: 2026-09-23 10:04:52.652496+00.
- **visual_language**: 9.00 (confidence 0.720). Forge pool-completion provisional score using current BLS/O*NET evidence and sampled Etsy competition. Lower confidence is intentional where exact employment sizing or clean marketplace decomposition is unavailable. Дата: 2026-09-23 10:04:52.652496+00.

### Концепции (0)

## 21. Heavy Equipment Field Mechanic
Ключ: `heavy_equipment_field_mechanic` · ID: `a3a8a361-3309-412c-a0a5-b5f054d059cb`

**Статус БД:** scored · **балл:** 76.45 · **confidence:** 74.10 · **coverage:** 100.00
**Аудитория:** Mobile heavy equipment mechanics and field-service technicians
**Категория:** occupational_identity
**Исследовательская аргументация:** Large and growing trade with strong tool/machine identity, but sampled Etsy evidence shows meaningful blue-collar/mechanic competition. Useful as a demand-rich benchmark and possible differentiated diagnostic-systems lane.
**Создано / обновлено:** 2026-09-23 09:34:00.70472+00 / 2026-09-23 09:34:30.438105+00

### Компоненты оценки ниши

- **channel_breadth**: 8.00 (confidence 0.650). Initial evidence-weighted Forge score from current BLS/O*NET data, sampled Etsy competition and practitioner-community signals. See niche_candidates.source_notes. This is prioritization research, not a sales forecast. Дата: 2026-09-23 09:34:30.438105+00.
- **competition_opportunity**: 3.50 (confidence 0.750). Initial evidence-weighted Forge score from current BLS/O*NET data, sampled Etsy competition and practitioner-community signals. See niche_candidates.source_notes. This is prioritization research, not a sales forecast. Дата: 2026-09-23 09:34:30.438105+00.
- **concept_depth**: 8.50 (confidence 0.650). Initial evidence-weighted Forge score from current BLS/O*NET data, sampled Etsy competition and practitioner-community signals. See niche_candidates.source_notes. This is prioritization research, not a sales forecast. Дата: 2026-09-23 09:34:30.438105+00.
- **demand_evidence**: 8.50 (confidence 0.850). Initial evidence-weighted Forge score from current BLS/O*NET data, sampled Etsy competition and practitioner-community signals. See niche_candidates.source_notes. This is prioritization research, not a sales forecast. Дата: 2026-09-23 09:34:30.438105+00.
- **founder_edge**: 7.50 (confidence 0.800). Initial evidence-weighted Forge score from current BLS/O*NET data, sampled Etsy competition and practitioner-community signals. See niche_candidates.source_notes. This is prioritization research, not a sales forecast. Дата: 2026-09-23 09:34:30.438105+00.
- **identity_intensity**: 8.50 (confidence 0.750). Initial evidence-weighted Forge score from current BLS/O*NET data, sampled Etsy competition and practitioner-community signals. See niche_candidates.source_notes. This is prioritization research, not a sales forecast. Дата: 2026-09-23 09:34:30.438105+00.
- **legal_safety**: 8.50 (confidence 0.650). Initial evidence-weighted Forge score from current BLS/O*NET data, sampled Etsy competition and practitioner-community signals. See niche_candidates.source_notes. This is prioritization research, not a sales forecast. Дата: 2026-09-23 09:34:30.438105+00.
- **purchase_motivation**: 8.00 (confidence 0.700). Initial evidence-weighted Forge score from current BLS/O*NET data, sampled Etsy competition and practitioner-community signals. See niche_candidates.source_notes. This is prioritization research, not a sales forecast. Дата: 2026-09-23 09:34:30.438105+00.
- **repeatability**: 8.00 (confidence 0.700). Initial evidence-weighted Forge score from current BLS/O*NET data, sampled Etsy competition and practitioner-community signals. See niche_candidates.source_notes. This is prioritization research, not a sales forecast. Дата: 2026-09-23 09:34:30.438105+00.
- **visual_language**: 9.00 (confidence 0.750). Initial evidence-weighted Forge score from current BLS/O*NET data, sampled Etsy competition and practitioner-community signals. See niche_candidates.source_notes. This is prioritization research, not a sales forecast. Дата: 2026-09-23 09:34:30.438105+00.

### Концепции (0)

## 22. Histotechnologist / Histology Technician
Ключ: `histotechnologist` · ID: `caa683d4-242b-4a38-b8e8-f0675ba32afc`

**Статус БД:** scored · **балл:** 77.90 · **confidence:** 73.40 · **coverage:** 100.00
**Аудитория:** Histotechnologists, histology technicians and pathology-lab tissue-processing staff
**Категория:** occupational_identity
**Исследовательская аргументация:** Extremely rich authentic workflow—embed, section, stain, inspect—with vivid tissue/microtome visual language. However Etsy already contains a meaningful histology-specific merch ecosystem, so opportunity depends on superior insider concepts rather than category novelty.
**Создано / обновлено:** 2026-09-23 09:42:54.27545+00 / 2026-09-23 09:43:36.792084+00

### Компоненты оценки ниши

- **channel_breadth**: 7.50 (confidence 0.620). Forge hidden-trades v2 initial score using current BLS/O*NET occupational evidence plus sampled Etsy marketplace depth. Scores prioritize buyer identity and whitespace, not raw occupation size. Benchmark niches intentionally receive competition penalties. Дата: 2026-09-23 09:43:36.792084+00.
- **competition_opportunity**: 4.80 (confidence 0.820). Forge hidden-trades v2 initial score using current BLS/O*NET occupational evidence plus sampled Etsy marketplace depth. Scores prioritize buyer identity and whitespace, not raw occupation size. Benchmark niches intentionally receive competition penalties. Дата: 2026-09-23 09:43:36.792084+00.
- **concept_depth**: 9.50 (confidence 0.800). Forge hidden-trades v2 initial score using current BLS/O*NET occupational evidence plus sampled Etsy marketplace depth. Scores prioritize buyer identity and whitespace, not raw occupation size. Benchmark niches intentionally receive competition penalties. Дата: 2026-09-23 09:43:36.792084+00.
- **demand_evidence**: 7.80 (confidence 0.720). Forge hidden-trades v2 initial score using current BLS/O*NET occupational evidence plus sampled Etsy marketplace depth. Scores prioritize buyer identity and whitespace, not raw occupation size. Benchmark niches intentionally receive competition penalties. Дата: 2026-09-23 09:43:36.792084+00.
- **founder_edge**: 2.00 (confidence 0.400). Forge hidden-trades v2 initial score using current BLS/O*NET occupational evidence plus sampled Etsy marketplace depth. Scores prioritize buyer identity and whitespace, not raw occupation size. Benchmark niches intentionally receive competition penalties. Дата: 2026-09-23 09:43:36.792084+00.
- **identity_intensity**: 8.50 (confidence 0.720). Forge hidden-trades v2 initial score using current BLS/O*NET occupational evidence plus sampled Etsy marketplace depth. Scores prioritize buyer identity and whitespace, not raw occupation size. Benchmark niches intentionally receive competition penalties. Дата: 2026-09-23 09:43:36.792084+00.
- **legal_safety**: 8.50 (confidence 0.660). Forge hidden-trades v2 initial score using current BLS/O*NET occupational evidence plus sampled Etsy marketplace depth. Scores prioritize buyer identity and whitespace, not raw occupation size. Benchmark niches intentionally receive competition penalties. Дата: 2026-09-23 09:43:36.792084+00.
- **purchase_motivation**: 8.00 (confidence 0.680). Forge hidden-trades v2 initial score using current BLS/O*NET occupational evidence plus sampled Etsy marketplace depth. Scores prioritize buyer identity and whitespace, not raw occupation size. Benchmark niches intentionally receive competition penalties. Дата: 2026-09-23 09:43:36.792084+00.
- **repeatability**: 8.50 (confidence 0.700). Forge hidden-trades v2 initial score using current BLS/O*NET occupational evidence plus sampled Etsy marketplace depth. Scores prioritize buyer identity and whitespace, not raw occupation size. Benchmark niches intentionally receive competition penalties. Дата: 2026-09-23 09:43:36.792084+00.
- **visual_language**: 10.00 (confidence 0.840). Forge hidden-trades v2 initial score using current BLS/O*NET occupational evidence plus sampled Etsy marketplace depth. Scores prioritize buyer identity and whitespace, not raw occupation size. Benchmark niches intentionally receive competition penalties. Дата: 2026-09-23 09:43:36.792084+00.

### Концепции (0)

## 23. Industrial Engineering Technologist / Technician
Ключ: `industrial_engineering_technologist_technician` · ID: `3082674b-06d3-4af1-a463-7984ef084898`

**Статус БД:** scored · **балл:** 75.95 · **confidence:** 62.22 · **coverage:** 100.00
**Аудитория:** Industrial engineering technologists and technicians in manufacturing, automation and process improvement
**Категория:** occupational_identity
**Исследовательская аргументация:** Replacement-driven technical occupation with process-flow, time-study, layout, automation, efficiency and quality language. Exact technician identity appears much thinner than generic engineer/Lean/Six Sigma merch.
**Создано / обновлено:** 2026-09-23 09:56:40.513406+00 / 2026-09-23 09:56:40.513406+00

### Компоненты оценки ниши

- **channel_breadth**: 8.50 (confidence 0.620). Forge diversity-batch v3 score using current 2025-35 BLS/O*NET evidence plus sampled current Etsy competition. Where exact marketplace counts were unavailable, competition confidence is intentionally lower. Дата: 2026-09-23 09:56:40.513406+00.
- **competition_opportunity**: 8.50 (confidence 0.460). Forge diversity-batch v3 score using current 2025-35 BLS/O*NET evidence plus sampled current Etsy competition. Where exact marketplace counts were unavailable, competition confidence is intentionally lower. Дата: 2026-09-23 09:56:40.513406+00.
- **concept_depth**: 8.50 (confidence 0.660). Forge diversity-batch v3 score using current 2025-35 BLS/O*NET evidence plus sampled current Etsy competition. Where exact marketplace counts were unavailable, competition confidence is intentionally lower. Дата: 2026-09-23 09:56:40.513406+00.
- **demand_evidence**: 8.00 (confidence 0.900). Forge diversity-batch v3 score using current 2025-35 BLS/O*NET evidence plus sampled current Etsy competition. Where exact marketplace counts were unavailable, competition confidence is intentionally lower. Дата: 2026-09-23 09:56:40.513406+00.
- **founder_edge**: 2.00 (confidence 0.400). Forge diversity-batch v3 score using current 2025-35 BLS/O*NET evidence plus sampled current Etsy competition. Where exact marketplace counts were unavailable, competition confidence is intentionally lower. Дата: 2026-09-23 09:56:40.513406+00.
- **identity_intensity**: 6.50 (confidence 0.540). Forge diversity-batch v3 score using current 2025-35 BLS/O*NET evidence plus sampled current Etsy competition. Where exact marketplace counts were unavailable, competition confidence is intentionally lower. Дата: 2026-09-23 09:56:40.513406+00.
- **legal_safety**: 9.00 (confidence 0.660). Forge diversity-batch v3 score using current 2025-35 BLS/O*NET evidence plus sampled current Etsy competition. Where exact marketplace counts were unavailable, competition confidence is intentionally lower. Дата: 2026-09-23 09:56:40.513406+00.
- **purchase_motivation**: 6.50 (confidence 0.500). Forge diversity-batch v3 score using current 2025-35 BLS/O*NET evidence plus sampled current Etsy competition. Where exact marketplace counts were unavailable, competition confidence is intentionally lower. Дата: 2026-09-23 09:56:40.513406+00.
- **repeatability**: 7.50 (confidence 0.560). Forge diversity-batch v3 score using current 2025-35 BLS/O*NET evidence plus sampled current Etsy competition. Where exact marketplace counts were unavailable, competition confidence is intentionally lower. Дата: 2026-09-23 09:56:40.513406+00.
- **visual_language**: 8.00 (confidence 0.640). Forge diversity-batch v3 score using current 2025-35 BLS/O*NET evidence plus sampled current Etsy competition. Where exact marketplace counts were unavailable, competition confidence is intentionally lower. Дата: 2026-09-23 09:56:40.513406+00.

### Концепции (0)

## 24. Industrial Machinery Mechanic
Ключ: `industrial_machinery_mechanic` · ID: `2513707a-16e1-4a76-9b1e-4ad53dc55f9e`

**Статус БД:** shortlisted · **балл:** 79.85 · **confidence:** 79.78 · **coverage:** 100.00
**Аудитория:** Industrial machinery mechanics / maintenance technicians
**Категория:** occupational_identity
**Исследовательская аргументация:** Legacy Town Label occupational niche carried forward for re-evaluation under the new niche-first scoring engine. Existing artwork quality does not determine niche status.
**Создано / обновлено:** 2026-09-23 06:11:01.997287+00 / 2026-09-23 10:03:30.159451+00

### Компоненты оценки ниши

- **channel_breadth**: 8.50 (confidence 0.700). Legacy Forge/Town Label niche rescored under the unified Forge rubric using current 2025-35 BLS data plus the 2026-09-21/22 marketplace and IP research already stored in merch.research_notes. Existing visual rejection does not count as niche rejection. Дата: 2026-09-23 09:44:55.053118+00.
- **competition_opportunity**: 3.50 (confidence 0.860). Legacy Forge/Town Label niche rescored under the unified Forge rubric using current 2025-35 BLS data plus the 2026-09-21/22 marketplace and IP research already stored in merch.research_notes. Existing visual rejection does not count as niche rejection. Дата: 2026-09-23 09:44:55.053118+00.
- **concept_depth**: 9.00 (confidence 0.760). Legacy Forge/Town Label niche rescored under the unified Forge rubric using current 2025-35 BLS data plus the 2026-09-21/22 marketplace and IP research already stored in merch.research_notes. Existing visual rejection does not count as niche rejection. Дата: 2026-09-23 09:44:55.053118+00.
- **demand_evidence**: 9.50 (confidence 0.940). Legacy Forge/Town Label niche rescored under the unified Forge rubric using current 2025-35 BLS data plus the 2026-09-21/22 marketplace and IP research already stored in merch.research_notes. Existing visual rejection does not count as niche rejection. Дата: 2026-09-23 09:44:55.053118+00.
- **founder_edge**: 4.00 (confidence 0.550). Legacy Forge/Town Label niche rescored under the unified Forge rubric using current 2025-35 BLS data plus the 2026-09-21/22 marketplace and IP research already stored in merch.research_notes. Existing visual rejection does not count as niche rejection. Дата: 2026-09-23 09:44:55.053118+00.
- **identity_intensity**: 8.50 (confidence 0.760). Legacy Forge/Town Label niche rescored under the unified Forge rubric using current 2025-35 BLS data plus the 2026-09-21/22 marketplace and IP research already stored in merch.research_notes. Existing visual rejection does not count as niche rejection. Дата: 2026-09-23 09:44:55.053118+00.
- **legal_safety**: 8.50 (confidence 0.720). Legacy Forge/Town Label niche rescored under the unified Forge rubric using current 2025-35 BLS data plus the 2026-09-21/22 marketplace and IP research already stored in merch.research_notes. Existing visual rejection does not count as niche rejection. Дата: 2026-09-23 09:44:55.053118+00.
- **purchase_motivation**: 8.50 (confidence 0.720). Legacy Forge/Town Label niche rescored under the unified Forge rubric using current 2025-35 BLS data plus the 2026-09-21/22 marketplace and IP research already stored in merch.research_notes. Existing visual rejection does not count as niche rejection. Дата: 2026-09-23 09:44:55.053118+00.
- **repeatability**: 9.00 (confidence 0.720). Legacy Forge/Town Label niche rescored under the unified Forge rubric using current 2025-35 BLS data plus the 2026-09-21/22 marketplace and IP research already stored in merch.research_notes. Existing visual rejection does not count as niche rejection. Дата: 2026-09-23 09:44:55.053118+00.
- **visual_language**: 9.00 (confidence 0.800). Legacy Forge/Town Label niche rescored under the unified Forge rubric using current 2025-35 BLS data plus the 2026-09-21/22 marketplace and IP research already stored in merch.research_notes. Existing visual rejection does not count as niche rejection. Дата: 2026-09-23 09:44:55.053118+00.

### Концепции (12)

#### Industrial — bearing / vibration / alignment
`industrial_bearing_vibration_alignment` · ID `4a6c3f0a-1705-4b1b-8d2e-4ce815cf4992`

**Интерпретация:** Исследовательский кандидат; одобрение владельца не зафиксировано
**Статус БД:** scored · **балл:** 88.75 · **confidence:** 68.17 · **coverage:** 100.00
**Текст / хук:** BEARING • VIBRATION • ALIGNMENT
**Идея:** Industrial — bearing / vibration / alignment. Core hook: BEARING • VIBRATION • ALIGNMENT. Factory machinery diagnosis, precision maintenance, power transmission and uptime. Execution must stay original and descriptive; avoid employer, OEM, certification-body, association and proprietary-interface branding.
**Покупатель:** Industrial machinery mechanics and maintenance technicians
**Причина покупки:** Identity purchase for industrial machinery mechanics and maintenance technicians who recognize the real workflow/systems language.
**Отличие:** Insider technical technical map direction intended to avoid generic profession-title, retro-badge, skull, flag, coffee and parody templates.
**Визуальное направление:** Condition/precision-maintenance language with shaft centerline, bearing and vibration-spectrum motifs.
**Создано / обновлено:** 2026-09-23 09:48:50.541446+00 / 2026-09-23 09:55:40.114238+00

Компоненты оценки:
- **buyer_desire**: 8.45 (confidence 0.670). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **clarity_at_glance**: 7.80 (confidence 0.670). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **distinctiveness**: 9.30 (confidence 0.670). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **giftability**: 7.50 (confidence 0.670). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **insider_resonance**: 9.35 (confidence 0.700). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **ip_safety**: 8.60 (confidence 0.670). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **niche_fit**: 9.34 (confidence 0.700). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **visual_potential**: 9.65 (confidence 0.700). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.

#### Industrial — conveyor drive system
`industrial_conveyor_drive_system` · ID `77d12a7a-5128-4a58-8905-4391a1f2fe36`

**Интерпретация:** Исследовательский кандидат; одобрение владельца не зафиксировано
**Статус БД:** scored · **балл:** 88.14 · **confidence:** 69.17 · **coverage:** 100.00
**Текст / хук:** DRIVE • BELT • ROLLER • LOAD
**Идея:** Industrial — conveyor drive system. Core hook: DRIVE • BELT • ROLLER • LOAD. Factory machinery diagnosis, precision maintenance, power transmission and uptime. Execution must stay original and descriptive; avoid employer, OEM, certification-body, association and proprietary-interface branding.
**Покупатель:** Industrial machinery mechanics and maintenance technicians
**Причина покупки:** Identity purchase for industrial machinery mechanics and maintenance technicians who recognize the real workflow/systems language.
**Отличие:** Insider technical system map direction intended to avoid generic profession-title, retro-badge, skull, flag, coffee and parody templates.
**Визуальное направление:** Simplified conveyor-drive schematic that avoids generic wrench/skull mechanic imagery.
**Создано / обновлено:** 2026-09-23 09:48:50.541446+00 / 2026-09-23 09:55:40.114238+00

Компоненты оценки:
- **buyer_desire**: 8.45 (confidence 0.680). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **clarity_at_glance**: 8.17 (confidence 0.680). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **distinctiveness**: 9.00 (confidence 0.680). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **giftability**: 7.57 (confidence 0.680). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **insider_resonance**: 9.10 (confidence 0.710). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **ip_safety**: 8.80 (confidence 0.680). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **niche_fit**: 9.34 (confidence 0.710). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **visual_potential**: 9.60 (confidence 0.710). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.

#### Industrial — maintenance loop
`industrial_lube_inspect_adjust_repair` · ID `873586e8-a2db-4396-88fd-2956506b0291`

**Интерпретация:** Исследовательский кандидат; одобрение владельца не зафиксировано
**Статус БД:** scored · **балл:** 84.40 · **confidence:** 67.17 · **coverage:** 100.00
**Текст / хук:** LUBE • INSPECT • ADJUST • REPAIR
**Идея:** Industrial — maintenance loop. Core hook: LUBE • INSPECT • ADJUST • REPAIR. Factory machinery diagnosis, precision maintenance, power transmission and uptime. Execution must stay original and descriptive; avoid employer, OEM, certification-body, association and proprietary-interface branding.
**Покупатель:** Industrial machinery mechanics and maintenance technicians
**Причина покупки:** Identity purchase for industrial machinery mechanics and maintenance technicians who recognize the real workflow/systems language.
**Отличие:** Insider technical workflow direction intended to avoid generic profession-title, retro-badge, skull, flag, coffee and parody templates.
**Визуальное направление:** Compact maintenance-service loop with original bearing/drive symbols.
**Создано / обновлено:** 2026-09-23 09:48:50.541446+00 / 2026-09-23 09:55:40.114238+00

Компоненты оценки:
- **buyer_desire**: 8.05 (confidence 0.660). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **clarity_at_glance**: 9.10 (confidence 0.660). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **distinctiveness**: 8.20 (confidence 0.660). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **giftability**: 8.00 (confidence 0.660). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **insider_resonance**: 8.70 (confidence 0.690). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **ip_safety**: 9.00 (confidence 0.660). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **niche_fit**: 9.24 (confidence 0.690). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **visual_potential**: 8.30 (confidence 0.690). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.

#### Industrial Machinery — machine systems
`industrial_machine_systems` · ID `645bd4bb-d3de-4f61-8763-52fc6a7e9a10`

**Интерпретация:** Исторический: снят после owner review; не возвращать автоматически
**Статус БД:** scored · **балл:** 90.07 · **confidence:** 74.24 · **coverage:** 100.00
**Текст / хук:** MACHINE SYSTEMS | MOTORS • CONVEYORS • DRIVES
**Идея:** Industrial Machinery Mechanic professional machine-systems graphic using the full occupational title plus MACHINE SYSTEMS, MOTORS • CONVEYORS • DRIVES, and DIAGNOSE • ALIGN • LUBRICATE • REPAIR. Research proof A uses an original motor-conveyor-drive schematic instead of skulls, crossed wrenches, gears, bulldog mascots, or generic maintenance slogans.
**Покупатель:** Industrial machinery mechanics / maintenance technicians
**Отличие:** Industrial maintenance apparel is crowded with skulls, wrenches, bulldog mascots, generic maintenance identity, precision slogans and reliability messaging. Candidate proceeds only with a machine-systems schematic angle.
**retired_reason:** failed purchase-trigger quality bar after owner review
**Создано / обновлено:** 2026-09-23 06:11:42.741293+00 / 2026-09-23 23:40:31.847823+00

Компоненты оценки:
- **buyer_desire**: 8.59 (confidence 0.739). Unified Forge concept-depth score. Profile captures the concept form (technical map, diagnostic, system map, workflow, process or terminology); a small stored concept bias and bounded niche-quality adjustment prevent identical form scores across materially different niches. No visual was generated. Federal/common-law phrase review remains a separate gate. Дата: 2026-09-23 09:51:32.257179+00.
- **clarity_at_glance**: 8.10 (confidence 0.717). Unified Forge concept-depth score. Profile captures the concept form (technical map, diagnostic, system map, workflow, process or terminology); a small stored concept bias and bounded niche-quality adjustment prevent identical form scores across materially different niches. No visual was generated. Federal/common-law phrase review remains a separate gate. Дата: 2026-09-23 09:51:32.257179+00.
- **distinctiveness**: 9.30 (confidence 0.754). Unified Forge concept-depth score. Profile captures the concept form (technical map, diagnostic, system map, workflow, process or terminology); a small stored concept bias and bounded niche-quality adjustment prevent identical form scores across materially different niches. No visual was generated. Federal/common-law phrase review remains a separate gate. Дата: 2026-09-23 09:51:32.257179+00.
- **giftability**: 7.59 (confidence 0.694). Unified Forge concept-depth score. Profile captures the concept form (technical map, diagnostic, system map, workflow, process or terminology); a small stored concept bias and bounded niche-quality adjustment prevent identical form scores across materially different niches. No visual was generated. Federal/common-law phrase review remains a separate gate. Дата: 2026-09-23 09:51:32.257179+00.
- **insider_resonance**: 9.30 (confidence 0.769). Unified Forge concept-depth score. Profile captures the concept form (technical map, diagnostic, system map, workflow, process or terminology); a small stored concept bias and bounded niche-quality adjustment prevent identical form scores across materially different niches. No visual was generated. Federal/common-law phrase review remains a separate gate. Дата: 2026-09-23 09:51:32.257179+00.
- **ip_safety**: 9.00 (confidence 0.550). Unified Forge concept-depth score. Profile captures the concept form (technical map, diagnostic, system map, workflow, process or terminology); a small stored concept bias and bounded niche-quality adjustment prevent identical form scores across materially different niches. No visual was generated. Federal/common-law phrase review remains a separate gate. Дата: 2026-09-23 09:51:32.257179+00.
- **niche_fit**: 9.69 (confidence 0.777). Unified Forge concept-depth score. Profile captures the concept form (technical map, diagnostic, system map, workflow, process or terminology); a small stored concept bias and bounded niche-quality adjustment prevent identical form scores across materially different niches. No visual was generated. Federal/common-law phrase review remains a separate gate. Дата: 2026-09-23 09:51:32.257179+00.
- **visual_potential**: 9.90 (confidence 0.792). Unified Forge concept-depth score. Profile captures the concept form (technical map, diagnostic, system map, workflow, process or terminology); a small stored concept bias and bounded niche-quality adjustment prevent identical form scores across materially different niches. No visual was generated. Federal/common-law phrase review remains a separate gate. Дата: 2026-09-23 09:51:32.257179+00.

#### Industrial — motor / coupling / gearbox
`industrial_motor_coupling_gearbox` · ID `e573b044-9875-4d7b-a762-186b9664d615`

**Интерпретация:** Исследовательский кандидат; одобрение владельца не зафиксировано
**Статус БД:** scored · **балл:** 88.75 · **confidence:** 69.17 · **coverage:** 100.00
**Текст / хук:** MOTOR → COUPLING → GEARBOX
**Идея:** Industrial — motor / coupling / gearbox. Core hook: MOTOR → COUPLING → GEARBOX. Factory machinery diagnosis, precision maintenance, power transmission and uptime. Execution must stay original and descriptive; avoid employer, OEM, certification-body, association and proprietary-interface branding.
**Покупатель:** Industrial machinery mechanics and maintenance technicians
**Причина покупки:** Identity purchase for industrial machinery mechanics and maintenance technicians who recognize the real workflow/systems language.
**Отличие:** Insider technical system map direction intended to avoid generic profession-title, retro-badge, skull, flag, coffee and parody templates.
**Визуальное направление:** Original machine-train schematic emphasizing power transmission components.
**Создано / обновлено:** 2026-09-23 09:48:50.541446+00 / 2026-09-23 10:03:30.159451+00

Компоненты оценки:
- **buyer_desire**: 8.55 (confidence 0.680). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **clarity_at_glance**: 8.20 (confidence 0.680). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **distinctiveness**: 9.10 (confidence 0.680). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **giftability**: 7.60 (confidence 0.680). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **insider_resonance**: 9.15 (confidence 0.710). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **ip_safety**: 8.80 (confidence 0.680). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **niche_fit**: 9.34 (confidence 0.710). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **visual_potential**: 9.65 (confidence 0.710). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.

#### Industrial — symptom to verified fix
`industrial_symptom_cause_correct_verify` · ID `cd8d99c7-1f06-4b72-a308-7548104b8c6d`

**Интерпретация:** Исследовательский кандидат; одобрение владельца не зафиксировано
**Статус БД:** scored · **балл:** 88.72 · **confidence:** 69.17 · **coverage:** 100.00
**Текст / хук:** SYMPTOM → CAUSE → CORRECT → VERIFY
**Идея:** Industrial — symptom to verified fix. Core hook: SYMPTOM → CAUSE → CORRECT → VERIFY. Factory machinery diagnosis, precision maintenance, power transmission and uptime. Execution must stay original and descriptive; avoid employer, OEM, certification-body, association and proprietary-interface branding.
**Покупатель:** Industrial machinery mechanics and maintenance technicians
**Причина покупки:** Identity purchase for industrial machinery mechanics and maintenance technicians who recognize the real workflow/systems language.
**Отличие:** Insider technical diagnostic direction intended to avoid generic profession-title, retro-badge, skull, flag, coffee and parody templates.
**Визуальное направление:** Troubleshooting logic diagram for industrial machinery, grounded in diagnosis rather than generic repair slogans.
**Создано / обновлено:** 2026-09-23 09:48:50.541446+00 / 2026-09-23 09:55:40.114238+00

Компоненты оценки:
- **buyer_desire**: 8.65 (confidence 0.680). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **clarity_at_glance**: 8.57 (confidence 0.680). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **distinctiveness**: 9.00 (confidence 0.680). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **giftability**: 7.87 (confidence 0.680). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **insider_resonance**: 9.40 (confidence 0.710). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **ip_safety**: 8.70 (confidence 0.680). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **niche_fit**: 9.44 (confidence 0.710). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **visual_potential**: 8.90 (confidence 0.710). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.

#### Industrial — uptime maintenance
`industrial_uptime_pm_condition_repair` · ID `baff68e8-c5eb-4b6e-b607-44657ef1cb46`

**Интерпретация:** Исследовательский кандидат; одобрение владельца не зафиксировано
**Статус БД:** scored · **балл:** 86.50 · **confidence:** 68.17 · **coverage:** 100.00
**Текст / хук:** PM • CONDITION • REPAIR • UPTIME
**Идея:** Industrial — uptime maintenance. Core hook: PM • CONDITION • REPAIR • UPTIME. Factory machinery diagnosis, precision maintenance, power transmission and uptime. Execution must stay original and descriptive; avoid employer, OEM, certification-body, association and proprietary-interface branding.
**Покупатель:** Industrial machinery mechanics and maintenance technicians
**Причина покупки:** Identity purchase for industrial machinery mechanics and maintenance technicians who recognize the real workflow/systems language.
**Отличие:** Insider technical process direction intended to avoid generic profession-title, retro-badge, skull, flag, coffee and parody templates.
**Визуальное направление:** Reliability-focused composition linking planned maintenance, condition checks and repairs to machine availability.
**Создано / обновлено:** 2026-09-23 09:48:50.541446+00 / 2026-09-23 09:55:40.114238+00

Компоненты оценки:
- **buyer_desire**: 8.25 (confidence 0.670). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **clarity_at_glance**: 8.73 (confidence 0.670). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **distinctiveness**: 8.60 (confidence 0.670). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **giftability**: 7.83 (confidence 0.670). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **insider_resonance**: 9.05 (confidence 0.700). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **ip_safety**: 8.80 (confidence 0.670). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **niche_fit**: 9.34 (confidence 0.700). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **visual_potential**: 8.85 (confidence 0.700). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.

#### Industrial maintenance — impossible request
`v4_ind_fix_without_stop` · ID `408d48ac-ac24-4807-bdfe-ddee6c241f0d`

**Интерпретация:** Исследовательский кандидат; одобрение владельца не зафиксировано
**Статус БД:** scored · **балл:** 89.79 · **confidence:** 70.32 · **coverage:** 100.00
**Текст / хук:** FIX IT. DON'T STOP IT. NEED IT YESTERDAY.
**Идея:** Turn the recurring contradiction 'fix it but do not stop it' into the joke.
**Покупатель:** Industrial machinery mechanics / maintenance technicians
**Причина покупки:** High-recognition shop-floor absurdity with strong coworker giftability.
**Отличие:** The concept is the contradiction between demands, not a list of machine parts.
**Визуальное направление:** Impossible three-way warning sign / triangle composition.
**Создано / обновлено:** 2026-09-23 19:58:09.189566+00 / 2026-09-24 05:05:38.621539+00

Компоненты оценки:
- **buyer_desire**: 9.10 (confidence 0.700). purchase_trigger_v2 preliminary score; gate passed; trigger=work_absurdity Дата: 2026-09-23 19:59:53.152527+00.
- **clarity_at_glance**: 9.30 (confidence 0.760). purchase_trigger_v2 preliminary score; gate passed; trigger=work_absurdity Дата: 2026-09-23 19:59:53.152527+00.
- **distinctiveness**: 8.70 (confidence 0.700). purchase_trigger_v2 preliminary score; gate passed; trigger=work_absurdity Дата: 2026-09-23 19:59:53.152527+00.
- **giftability**: 8.80 (confidence 0.670). purchase_trigger_v2 preliminary score; gate passed; trigger=work_absurdity Дата: 2026-09-23 19:59:53.152527+00.
- **insider_resonance**: 9.30 (confidence 0.720). purchase_trigger_v2 preliminary score; gate passed; trigger=work_absurdity Дата: 2026-09-23 19:59:53.152527+00.
- **ip_safety**: 8.90 (confidence 0.600). purchase_trigger_v2 preliminary score; gate passed; trigger=work_absurdity Дата: 2026-09-23 19:59:53.152527+00.
- **niche_fit**: 9.20 (confidence 0.720). purchase_trigger_v2 preliminary score; gate passed; trigger=work_absurdity Дата: 2026-09-23 19:59:53.152527+00.
- **visual_potential**: 8.50 (confidence 0.720). purchase_trigger_v2 preliminary score; gate passed; trigger=work_absurdity Дата: 2026-09-23 19:59:53.152527+00.

#### Industrial maintenance — found the bigger problem
`v4_ind_found_future_shutdown` · ID `1e31825c-ba2a-4d39-b45b-63152c57ad2e`

**Интерпретация:** Исследовательский кандидат; одобрение владельца не зафиксировано
**Статус БД:** scored · **балл:** 86.62 · **confidence:** 70.32 · **coverage:** 100.00
**Текст / хук:** YOU CALLED ABOUT A NOISE. I FOUND NEXT WEEK'S DOWNTIME.
**Идея:** Pride in finding the hidden failure before it becomes catastrophic.
**Покупатель:** Industrial machinery mechanics / maintenance technicians
**Причина покупки:** Competence/status: the wearer catches what others miss.
**Отличие:** The hook is prevention and foresight, not components.
**Визуальное направление:** Small vibration/noise icon expanding into a prevented shutdown graphic.
**Создано / обновлено:** 2026-09-23 19:58:09.189566+00 / 2026-09-24 05:05:38.621539+00

Компоненты оценки:
- **buyer_desire**: 8.50 (confidence 0.700). purchase_trigger_v2 preliminary score; gate passed; trigger=diagnostic_pride Дата: 2026-09-23 19:59:53.152527+00.
- **clarity_at_glance**: 8.70 (confidence 0.760). purchase_trigger_v2 preliminary score; gate passed; trigger=diagnostic_pride Дата: 2026-09-23 19:59:53.152527+00.
- **distinctiveness**: 8.60 (confidence 0.700). purchase_trigger_v2 preliminary score; gate passed; trigger=diagnostic_pride Дата: 2026-09-23 19:59:53.152527+00.
- **giftability**: 8.10 (confidence 0.670). purchase_trigger_v2 preliminary score; gate passed; trigger=diagnostic_pride Дата: 2026-09-23 19:59:53.152527+00.
- **insider_resonance**: 9.00 (confidence 0.720). purchase_trigger_v2 preliminary score; gate passed; trigger=diagnostic_pride Дата: 2026-09-23 19:59:53.152527+00.
- **ip_safety**: 8.90 (confidence 0.600). purchase_trigger_v2 preliminary score; gate passed; trigger=diagnostic_pride Дата: 2026-09-23 19:59:53.152527+00.
- **niche_fit**: 9.30 (confidence 0.720). purchase_trigger_v2 preliminary score; gate passed; trigger=diagnostic_pride Дата: 2026-09-23 19:59:53.152527+00.
- **visual_potential**: 8.80 (confidence 0.720). purchase_trigger_v2 preliminary score; gate passed; trigger=diagnostic_pride Дата: 2026-09-23 19:59:53.152527+00.

#### Industrial maintenance — Friday 4:58
`v4_ind_friday_458` · ID `5beead04-a58f-4e25-87bc-e8f5d8f67fb6`

**Интерпретация:** Исследовательский кандидат; одобрение владельца не зафиксировано
**Статус БД:** scored · **балл:** 88.74 · **confidence:** 70.32 · **coverage:** 100.00
**Текст / хук:** OF COURSE IT BROKE AT 4:58 FRIDAY.
**Идея:** The worst possible problem appears at the exact end of the week.
**Покупатель:** Industrial machinery mechanics / maintenance technicians
**Причина покупки:** Shift-life solidarity and giftable gallows humor.
**Отличие:** Timing is the premise; niche context comes from a machine-down visual.
**Визуальное направление:** Clock at 4:58 with alarm beacon / wrench silhouette.
**Создано / обновлено:** 2026-09-23 19:58:09.189566+00 / 2026-09-24 05:05:38.621539+00

Компоненты оценки:
- **buyer_desire**: 9.00 (confidence 0.700). purchase_trigger_v2 preliminary score; gate passed; trigger=timing_humor Дата: 2026-09-23 19:59:53.152527+00.
- **clarity_at_glance**: 9.30 (confidence 0.760). purchase_trigger_v2 preliminary score; gate passed; trigger=timing_humor Дата: 2026-09-23 19:59:53.152527+00.
- **distinctiveness**: 8.40 (confidence 0.700). purchase_trigger_v2 preliminary score; gate passed; trigger=timing_humor Дата: 2026-09-23 19:59:53.152527+00.
- **giftability**: 8.90 (confidence 0.670). purchase_trigger_v2 preliminary score; gate passed; trigger=timing_humor Дата: 2026-09-23 19:59:53.152527+00.
- **insider_resonance**: 9.10 (confidence 0.720). purchase_trigger_v2 preliminary score; gate passed; trigger=timing_humor Дата: 2026-09-23 19:59:53.152527+00.
- **ip_safety**: 8.90 (confidence 0.600). purchase_trigger_v2 preliminary score; gate passed; trigger=timing_humor Дата: 2026-09-23 19:59:53.152527+00.
- **niche_fit**: 9.00 (confidence 0.720). purchase_trigger_v2 preliminary score; gate passed; trigger=timing_humor Дата: 2026-09-23 19:59:53.152527+00.
- **visual_potential**: 8.50 (confidence 0.720). purchase_trigger_v2 preliminary score; gate passed; trigger=timing_humor Дата: 2026-09-23 19:59:53.152527+00.

#### Industrial maintenance — failure only unwatched
`v4_ind_machine_witness` · ID `0bf7e41e-c43b-4061-aa07-6c137037256a`

**Интерпретация:** V4: понижен редакционным отбором, сохранен в истории
**Статус БД:** scored · **балл:** 89.20 · **confidence:** 70.32 · **coverage:** 100.00
**Текст / хук:** IT ONLY FAILS WHEN I'M NOT LOOKING.
**Идея:** Give the machine a mischievous personality: it fails only when the technician is absent.
**Покупатель:** Industrial machinery mechanics / maintenance technicians
**Причина покупки:** Humor around intermittent faults and the technician's helpless relationship with them.
**Отличие:** A humanized problem rather than a technical fault list.
**Визуальное направление:** Sneaky machine eyes / technician turning around; generic industrial silhouette.
**editorial_reason:** generic cross-domain intermittent-fault phrasing
**Создано / обновлено:** 2026-09-23 19:58:09.189566+00 / 2026-09-24 05:05:38.621539+00

Компоненты оценки:
- **buyer_desire**: 8.90 (confidence 0.700). purchase_trigger_v2 preliminary score; gate passed; trigger=intermittent_fault_humor Дата: 2026-09-23 19:59:53.152527+00.
- **clarity_at_glance**: 9.20 (confidence 0.760). purchase_trigger_v2 preliminary score; gate passed; trigger=intermittent_fault_humor Дата: 2026-09-23 19:59:53.152527+00.
- **distinctiveness**: 8.60 (confidence 0.700). purchase_trigger_v2 preliminary score; gate passed; trigger=intermittent_fault_humor Дата: 2026-09-23 19:59:53.152527+00.
- **giftability**: 8.80 (confidence 0.670). purchase_trigger_v2 preliminary score; gate passed; trigger=intermittent_fault_humor Дата: 2026-09-23 19:59:53.152527+00.
- **insider_resonance**: 9.30 (confidence 0.720). purchase_trigger_v2 preliminary score; gate passed; trigger=intermittent_fault_humor Дата: 2026-09-23 19:59:53.152527+00.
- **ip_safety**: 8.90 (confidence 0.600). purchase_trigger_v2 preliminary score; gate passed; trigger=intermittent_fault_humor Дата: 2026-09-23 19:59:53.152527+00.
- **niche_fit**: 9.20 (confidence 0.720). purchase_trigger_v2 preliminary score; gate passed; trigger=intermittent_fault_humor Дата: 2026-09-23 19:59:53.152527+00.
- **visual_potential**: 8.70 (confidence 0.720). purchase_trigger_v2 preliminary score; gate passed; trigger=intermittent_fault_humor Дата: 2026-09-23 19:59:53.152527+00.

#### Industrial maintenance — technician effect
`v4_ind_tech_arrives` · ID `b0432ae0-2f5d-4569-a0ca-de0803d65298`

**Интерпретация:** Исследовательский кандидат; одобрение владельца не зафиксировано
**Статус БД:** scored · **балл:** 86.83 · **confidence:** 70.32 · **coverage:** 100.00
**Текст / хук:** IT WAS BROKEN UNTIL I GOT HERE.
**Идея:** The machine mysteriously behaves the moment maintenance arrives.
**Покупатель:** Industrial machinery mechanics / maintenance technicians
**Причина покупки:** Light status joke: the wearer is either a miracle worker or cursed witness.
**Отличие:** No technical terms required; situation is the hook.
**Визуальное направление:** Machine with angel halo / maintenance tech silhouette; avoid brand-specific machinery.
**Создано / обновлено:** 2026-09-23 19:58:09.189566+00 / 2026-09-24 05:05:38.621539+00

Компоненты оценки:
- **buyer_desire**: 8.60 (confidence 0.700). purchase_trigger_v2 preliminary score; gate passed; trigger=competence_humor Дата: 2026-09-23 19:59:53.152527+00.
- **clarity_at_glance**: 9.10 (confidence 0.760). purchase_trigger_v2 preliminary score; gate passed; trigger=competence_humor Дата: 2026-09-23 19:59:53.152527+00.
- **distinctiveness**: 8.30 (confidence 0.700). purchase_trigger_v2 preliminary score; gate passed; trigger=competence_humor Дата: 2026-09-23 19:59:53.152527+00.
- **giftability**: 8.60 (confidence 0.670). purchase_trigger_v2 preliminary score; gate passed; trigger=competence_humor Дата: 2026-09-23 19:59:53.152527+00.
- **insider_resonance**: 9.00 (confidence 0.720). purchase_trigger_v2 preliminary score; gate passed; trigger=competence_humor Дата: 2026-09-23 19:59:53.152527+00.
- **ip_safety**: 8.90 (confidence 0.600). purchase_trigger_v2 preliminary score; gate passed; trigger=competence_humor Дата: 2026-09-23 19:59:53.152527+00.
- **niche_fit**: 9.10 (confidence 0.720). purchase_trigger_v2 preliminary score; gate passed; trigger=competence_humor Дата: 2026-09-23 19:59:53.152527+00.
- **visual_potential**: 8.50 (confidence 0.720). purchase_trigger_v2 preliminary score; gate passed; trigger=competence_humor Дата: 2026-09-23 19:59:53.152527+00.

## 25. Instrumentation & Controls Technician
Ключ: `instrumentation_controls_technician` · ID: `17f0cbd7-4e06-4f60-95a7-4522529502f4`

**Статус БД:** shortlisted · **балл:** 79.65 · **confidence:** 73.66 · **coverage:** 100.00
**Аудитория:** Instrumentation, process-control, automation and I&C technicians
**Категория:** occupational_identity
**Исследовательская аргументация:** Very strong insider vocabulary (loops, calibration, transmitters, PLCs, fault finding) with active practitioner community and surprisingly thin sampled merch.
**Создано / обновлено:** 2026-09-23 09:34:00.70472+00 / 2026-09-23 10:14:18.633101+00

### Компоненты оценки ниши

- **channel_breadth**: 8.00 (confidence 0.720). Initial evidence-weighted Forge score from current BLS/O*NET data, sampled Etsy competition and practitioner-community signals. See niche_candidates.source_notes. This is prioritization research, not a sales forecast. Instrumentation/control identity spans utilities, manufacturing, water/process industries and automation; confidence raised from cross-industry practitioner evidence. Дата: 2026-09-23 09:34:30.438105+00.
- **competition_opportunity**: 8.80 (confidence 0.680). Initial evidence-weighted Forge score from current BLS/O*NET data, sampled Etsy competition and practitioner-community signals. See niche_candidates.source_notes. This is prioritization research, not a sales forecast. Sampled marketplace search remains sparse for exact instrumentation/I&C technician identity relative to generic automation/electrical merch; evidence is directional, not exhaustive. Дата: 2026-09-23 09:34:30.438105+00.
- **concept_depth**: 9.50 (confidence 0.840). Initial evidence-weighted Forge score from current BLS/O*NET data, sampled Etsy competition and practitioner-community signals. See niche_candidates.source_notes. This is prioritization research, not a sales forecast. O*NET titles/tasks and practitioner discussions independently support multiple authentic hooks: loop checks, 4-20 mA, calibration, PLC I/O, sensors, controllers, valves, alarms/interlocks and troubleshooting. Дата: 2026-09-23 09:34:30.438105+00.
- **demand_evidence**: 6.50 (confidence 0.680). Initial evidence-weighted Forge score from current BLS/O*NET data, sampled Etsy competition and practitioner-community signals. See niche_candidates.source_notes. This is prioritization research, not a sales forecast. O*NET 2026 directly maps Instrumentation and Controls Technician / Instrument Technician / Process Control Technician / PLC Technician into the occupation family; still no clean standalone BLS headcount, so demand confidence remains moderate. Дата: 2026-09-23 09:34:30.438105+00.
- **founder_edge**: 2.00 (confidence 0.400). Initial evidence-weighted Forge score from current BLS/O*NET data, sampled Etsy competition and practitioner-community signals. See niche_candidates.source_notes. This is prioritization research, not a sales forecast. Дата: 2026-09-23 09:34:30.438105+00.
- **identity_intensity**: 8.00 (confidence 0.800). Initial evidence-weighted Forge score from current BLS/O*NET data, sampled Etsy competition and practitioner-community signals. See niche_candidates.source_notes. This is prioritization research, not a sales forecast. Current 2026 practitioner discussions consistently center instrumentation as a distinct technician identity with troubleshooting, calibration, PLC/DCS/HMI and process knowledge. Дата: 2026-09-23 09:34:30.438105+00.
- **legal_safety**: 8.50 (confidence 0.600). Initial evidence-weighted Forge score from current BLS/O*NET data, sampled Etsy competition and practitioner-community signals. See niche_candidates.source_notes. This is prioritization research, not a sales forecast. Дата: 2026-09-23 09:34:30.438105+00.
- **purchase_motivation**: 7.50 (confidence 0.740). Initial evidence-weighted Forge score from current BLS/O*NET data, sampled Etsy competition and practitioner-community signals. See niche_candidates.source_notes. This is prioritization research, not a sales forecast. Practitioner discussions show strong craft/status identity around fault finding, commissioning and plant responsibility; purchase motivation evidence improved but is not direct sales data. Дата: 2026-09-23 09:34:30.438105+00.
- **repeatability**: 8.50 (confidence 0.720). Initial evidence-weighted Forge score from current BLS/O*NET data, sampled Etsy competition and practitioner-community signals. See niche_candidates.source_notes. This is prioritization research, not a sales forecast. Multiple independent technical subdomains support series expansion; confidence raised from the broader task vocabulary. Дата: 2026-09-23 09:34:30.438105+00.
- **visual_language**: 9.50 (confidence 0.860). Initial evidence-weighted Forge score from current BLS/O*NET data, sampled Etsy competition and practitioner-community signals. See niche_candidates.source_notes. This is prioritization research, not a sales forecast. Current occupational/practitioner evidence strongly supports recognizable meters, transmitters, loops, process variables, PLC I/O, wiring and control-system visuals. Дата: 2026-09-23 09:34:30.438105+00.

### Концепции (14)

#### I&C — 4–20 mA loop
`ic_4_20ma_loop` · ID `139b0a1b-6706-4120-8d68-fdc05774f6be`

**Интерпретация:** Исследовательский кандидат; одобрение владельца не зафиксировано
**Статус БД:** scored · **балл:** 87.70 · **confidence:** 69.18 · **coverage:** 100.00
**Текст / хук:** 4–20 mA / PV → TX → CTRL → OUT
**Идея:** INSTRUMENTATION TECHNICIAN centered on 4–20 mA as the recognizable analog process-control signal, with a generic PV → transmitter → controller → output loop. Do not add third-party instrument brands.
**Покупатель:** Instrumentation and process-control technicians
**Причина покупки:** Immediate insider recognition and giftability among process-instrumentation workers.
**Отличие:** Very specific instrumentation cue; later IP/common-law screen still required before any exact headline is promoted.
**Визуальное направление:** Meter scale, loop current path, transmitter/controller blocks, restrained industrial labeling
**Создано / обновлено:** 2026-09-23 09:36:02.928333+00 / 2026-09-23 10:09:42.905504+00

Компоненты оценки:
- **buyer_desire**: 9.00 (confidence 0.720). Initial Forge concept score using current occupational terminology, sampled marketplace patterns and technical distinctiveness. No visual has been generated; exact phrases still require IP/common-law screening before promotion. Дата: 2026-09-23 09:36:38.256823+00.
- **clarity_at_glance**: 9.00 (confidence 0.720). Initial Forge concept score using current occupational terminology, sampled marketplace patterns and technical distinctiveness. No visual has been generated; exact phrases still require IP/common-law screening before promotion. Дата: 2026-09-23 09:36:38.256823+00.
- **distinctiveness**: 7.50 (confidence 0.550). Initial Forge concept score using current occupational terminology, sampled marketplace patterns and technical distinctiveness. No visual has been generated; exact phrases still require IP/common-law screening before promotion. Дата: 2026-09-23 09:36:38.256823+00.
- **giftability**: 8.50 (confidence 0.680). Initial Forge concept score using current occupational terminology, sampled marketplace patterns and technical distinctiveness. No visual has been generated; exact phrases still require IP/common-law screening before promotion. Дата: 2026-09-23 09:36:38.256823+00.
- **insider_resonance**: 10.00 (confidence 0.820). Initial Forge concept score using current occupational terminology, sampled marketplace patterns and technical distinctiveness. No visual has been generated; exact phrases still require IP/common-law screening before promotion. Дата: 2026-09-23 09:36:38.256823+00.
- **ip_safety**: 7.00 (confidence 0.500). Initial Forge concept score using current occupational terminology, sampled marketplace patterns and technical distinctiveness. No visual has been generated; exact phrases still require IP/common-law screening before promotion. Дата: 2026-09-23 09:36:38.256823+00.
- **niche_fit**: 10.00 (confidence 0.820). Initial Forge concept score using current occupational terminology, sampled marketplace patterns and technical distinctiveness. No visual has been generated; exact phrases still require IP/common-law screening before promotion. Дата: 2026-09-23 09:36:38.256823+00.
- **visual_potential**: 8.50 (confidence 0.660). Initial Forge concept score using current occupational terminology, sampled marketplace patterns and technical distinctiveness. No visual has been generated; exact phrases still require IP/common-law screening before promotion. Дата: 2026-09-23 09:36:38.256823+00.

#### I&C — alarm / interlock / permissive
`ic_alarm_interlock_permissive` · ID `a0498c90-fc56-4329-beab-ead85f1d2558`

**Интерпретация:** Исследовательский кандидат; одобрение владельца не зафиксировано
**Статус БД:** scored · **балл:** 86.94 · **confidence:** 67.17 · **coverage:** 100.00
**Текст / хук:** ALARM • INTERLOCK • PERMISSIVE
**Идея:** I&C — alarm / interlock / permissive. Core hook: ALARM • INTERLOCK • PERMISSIVE. Process measurement, control loops, field instruments, PLC I/O and fault finding. Execution must stay original and descriptive; avoid employer, OEM, certification-body, association and proprietary-interface branding.
**Покупатель:** Instrumentation and controls technicians
**Причина покупки:** Identity purchase for instrumentation and controls technicians who recognize the real workflow/systems language.
**Отличие:** Insider technical terminology direction intended to avoid generic profession-title, retro-badge, skull, flag, coffee and parody templates.
**Визуальное направление:** Control-protection terminology arranged as original logic blocks; identity graphic, not operating instructions.
**Создано / обновлено:** 2026-09-23 09:48:50.541446+00 / 2026-09-23 09:55:40.114238+00

Компоненты оценки:
- **buyer_desire**: 8.04 (confidence 0.660). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **clarity_at_glance**: 9.27 (confidence 0.660). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **distinctiveness**: 8.50 (confidence 0.660). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **giftability**: 8.17 (confidence 0.660). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **insider_resonance**: 9.50 (confidence 0.690). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **ip_safety**: 8.80 (confidence 0.660). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **niche_fit**: 9.43 (confidence 0.690). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **visual_potential**: 8.50 (confidence 0.690). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.

#### I&C — fault finding
`ic_fault_find_calibrate_verify_document` · ID `eb77925f-fde0-45f6-8519-8b533a0c23c2`

**Интерпретация:** Исследовательский кандидат; одобрение владельца не зафиксировано
**Статус БД:** scored · **балл:** 86.15 · **confidence:** 66.96 · **coverage:** 100.00
**Текст / хук:** FAULT FIND • CALIBRATE • VERIFY • DOCUMENT
**Идея:** INSTRUMENTATION & CONTROLS TECHNICIAN workflow built around FAULT FIND • CALIBRATE • VERIFY • DOCUMENT, with generic pressure/flow/level/temperature measurement cues and test equipment.
**Покупатель:** Instrumentation and process-control technicians
**Причина покупки:** Celebrates the diagnostic craft rather than a generic job title.
**Отличие:** Multi-instrument troubleshooting language offers deeper insider resonance.
**Визуальное направление:** Four-step technical service sequence; gauge/transmitter silhouettes and trace lines
**Создано / обновлено:** 2026-09-23 09:36:02.928333+00 / 2026-09-23 10:09:42.905504+00

Компоненты оценки:
- **buyer_desire**: 8.50 (confidence 0.660). Initial Forge concept score using current occupational terminology, sampled marketplace patterns and technical distinctiveness. No visual has been generated; exact phrases still require IP/common-law screening before promotion. Дата: 2026-09-23 09:36:38.256823+00.
- **clarity_at_glance**: 9.00 (confidence 0.700). Initial Forge concept score using current occupational terminology, sampled marketplace patterns and technical distinctiveness. No visual has been generated; exact phrases still require IP/common-law screening before promotion. Дата: 2026-09-23 09:36:38.256823+00.
- **distinctiveness**: 8.50 (confidence 0.640). Initial Forge concept score using current occupational terminology, sampled marketplace patterns and technical distinctiveness. No visual has been generated; exact phrases still require IP/common-law screening before promotion. Дата: 2026-09-23 09:36:38.256823+00.
- **giftability**: 8.00 (confidence 0.620). Initial Forge concept score using current occupational terminology, sampled marketplace patterns and technical distinctiveness. No visual has been generated; exact phrases still require IP/common-law screening before promotion. Дата: 2026-09-23 09:36:38.256823+00.
- **insider_resonance**: 9.00 (confidence 0.720). Initial Forge concept score using current occupational terminology, sampled marketplace patterns and technical distinctiveness. No visual has been generated; exact phrases still require IP/common-law screening before promotion. Дата: 2026-09-23 09:36:38.256823+00.
- **ip_safety**: 9.00 (confidence 0.680). Initial Forge concept score using current occupational terminology, sampled marketplace patterns and technical distinctiveness. No visual has been generated; exact phrases still require IP/common-law screening before promotion. Дата: 2026-09-23 09:36:38.256823+00.
- **niche_fit**: 9.50 (confidence 0.760). Initial Forge concept score using current occupational terminology, sampled marketplace patterns and technical distinctiveness. No visual has been generated; exact phrases still require IP/common-law screening before promotion. Дата: 2026-09-23 09:36:38.256823+00.
- **visual_potential**: 8.00 (confidence 0.620). Initial Forge concept score using current occupational terminology, sampled marketplace patterns and technical distinctiveness. No visual has been generated; exact phrases still require IP/common-law screening before promotion. Дата: 2026-09-23 09:36:38.256823+00.

#### I&C — loop check / zero / span
`ic_loop_check_zero_span` · ID `781a214c-ae1b-47dd-8a7f-686d97dd8d17`

**Интерпретация:** Исторический: снят после owner review; не возвращать автоматически
**Статус БД:** scored · **балл:** 89.30 · **confidence:** 69.17 · **coverage:** 100.00
**Текст / хук:** LOOP CHECK • ZERO • SPAN
**Идея:** I&C — loop check / zero / span. Core hook: LOOP CHECK • ZERO • SPAN. Process measurement, control loops, field instruments, PLC I/O and fault finding. Execution must stay original and descriptive; avoid employer, OEM, certification-body, association and proprietary-interface branding.
**Покупатель:** Instrumentation and controls technicians
**Причина покупки:** Identity purchase for instrumentation and controls technicians who recognize the real workflow/systems language.
**Отличие:** Insider technical diagnostic direction intended to avoid generic profession-title, retro-badge, skull, flag, coffee and parody templates.
**Визуальное направление:** Instrument-check identity with generic transmitter, meter and control-loop path; no vendor panel copied.
**retired_reason:** failed purchase-trigger quality bar after owner review
**Создано / обновлено:** 2026-09-23 09:48:50.541446+00 / 2026-09-23 23:40:31.847823+00

Компоненты оценки:
- **buyer_desire**: 8.74 (confidence 0.680). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **clarity_at_glance**: 8.60 (confidence 0.680). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **distinctiveness**: 9.10 (confidence 0.680). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **giftability**: 7.90 (confidence 0.680). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **insider_resonance**: 9.45 (confidence 0.710). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **ip_safety**: 8.70 (confidence 0.680). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **niche_fit**: 9.43 (confidence 0.710). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **visual_potential**: 8.95 (confidence 0.710). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.

#### I&C — measure / control / verify / log
`ic_measure_control_verify_log` · ID `09a8c799-11f5-41a9-b51a-469ef7c57308`

**Интерпретация:** Исследовательский кандидат; одобрение владельца не зафиксировано
**Статус БД:** scored · **балл:** 84.98 · **confidence:** 67.17 · **coverage:** 100.00
**Текст / хук:** MEASURE • CONTROL • VERIFY • LOG
**Идея:** I&C — measure / control / verify / log. Core hook: MEASURE • CONTROL • VERIFY • LOG. Process measurement, control loops, field instruments, PLC I/O and fault finding. Execution must stay original and descriptive; avoid employer, OEM, certification-body, association and proprietary-interface branding.
**Покупатель:** Instrumentation and controls technicians
**Причина покупки:** Identity purchase for instrumentation and controls technicians who recognize the real workflow/systems language.
**Отличие:** Insider technical workflow direction intended to avoid generic profession-title, retro-badge, skull, flag, coffee and parody templates.
**Визуальное направление:** Four-step process-control responsibility loop with transmitter/controller/record motifs.
**Создано / обновлено:** 2026-09-23 09:48:50.541446+00 / 2026-09-23 09:55:40.114238+00

Компоненты оценки:
- **buyer_desire**: 8.14 (confidence 0.660). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **clarity_at_glance**: 9.13 (confidence 0.660). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **distinctiveness**: 8.30 (confidence 0.660). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **giftability**: 8.03 (confidence 0.660). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **insider_resonance**: 8.75 (confidence 0.690). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **ip_safety**: 9.00 (confidence 0.660). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **niche_fit**: 9.23 (confidence 0.690). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **visual_potential**: 8.35 (confidence 0.690). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.

#### I&C — PLC I/O signal path
`ic_plc_io_signal_path` · ID `38a26514-6b4b-40c6-8f2e-0424f9a2c058`

**Интерпретация:** Исследовательский кандидат; одобрение владельца не зафиксировано
**Статус БД:** scored · **балл:** 88.11 · **confidence:** 68.17 · **coverage:** 100.00
**Текст / хук:** FIELD → I/O → LOGIC → OUTPUT
**Идея:** I&C — PLC I/O signal path. Core hook: FIELD → I/O → LOGIC → OUTPUT. Process measurement, control loops, field instruments, PLC I/O and fault finding. Execution must stay original and descriptive; avoid employer, OEM, certification-body, association and proprietary-interface branding.
**Покупатель:** Instrumentation and controls technicians
**Причина покупки:** Identity purchase for instrumentation and controls technicians who recognize the real workflow/systems language.
**Отличие:** Insider technical technical map direction intended to avoid generic profession-title, retro-badge, skull, flag, coffee and parody templates.
**Визуальное направление:** Generic PLC signal-chain concept without vendor ladder-logic/UI replication.
**Создано / обновлено:** 2026-09-23 09:48:50.541446+00 / 2026-09-23 09:55:40.114238+00

Компоненты оценки:
- **buyer_desire**: 8.34 (confidence 0.670). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **clarity_at_glance**: 7.77 (confidence 0.670). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **distinctiveness**: 9.20 (confidence 0.670). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **giftability**: 7.47 (confidence 0.670). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **insider_resonance**: 9.30 (confidence 0.700). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **ip_safety**: 8.60 (confidence 0.670). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **niche_fit**: 9.33 (confidence 0.700). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **visual_potential**: 9.60 (confidence 0.700). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.

#### I&C — four process variables
`ic_pressure_flow_level_temp` · ID `11d2c973-5e02-4714-b67c-8837b8dedcf3`

**Интерпретация:** Исследовательский кандидат; одобрение владельца не зафиксировано
**Статус БД:** scored · **балл:** 87.55 · **confidence:** 67.17 · **coverage:** 100.00
**Текст / хук:** PRESSURE • FLOW • LEVEL • TEMP
**Идея:** I&C — four process variables. Core hook: PRESSURE • FLOW • LEVEL • TEMP. Process measurement, control loops, field instruments, PLC I/O and fault finding. Execution must stay original and descriptive; avoid employer, OEM, certification-body, association and proprietary-interface branding.
**Покупатель:** Instrumentation and controls technicians
**Причина покупки:** Identity purchase for instrumentation and controls technicians who recognize the real workflow/systems language.
**Отличие:** Insider technical terminology direction intended to avoid generic profession-title, retro-badge, skull, flag, coffee and parody templates.
**Визуальное направление:** Four-variable instrumentation field with original transmitter/gauge symbols and a common control spine.
**Создано / обновлено:** 2026-09-23 09:48:50.541446+00 / 2026-09-23 09:55:40.114238+00

Компоненты оценки:
- **buyer_desire**: 8.14 (confidence 0.660). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **clarity_at_glance**: 9.30 (confidence 0.660). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **distinctiveness**: 8.60 (confidence 0.660). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **giftability**: 8.20 (confidence 0.660). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **insider_resonance**: 9.55 (confidence 0.690). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **ip_safety**: 8.80 (confidence 0.660). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **niche_fit**: 9.43 (confidence 0.690). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **visual_potential**: 8.55 (confidence 0.690). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.

#### I&C — process loop
`ic_process_loop_sense_transmit_control_verify` · ID `067e0a02-63c1-403e-8999-6fd78369a1bc`

**Интерпретация:** Исследовательский кандидат; одобрение владельца не зафиксировано
**Статус БД:** scored · **балл:** 88.85 · **confidence:** 70.50 · **coverage:** 100.00
**Текст / хук:** SENSE → TRANSMIT → CONTROL → VERIFY
**Идея:** INSTRUMENTATION & CONTROLS TECHNICIAN with a generic process loop: SENSE → TRANSMIT → CONTROL → VERIFY. Use abstract transmitter, controller/PLC and final-control-element symbols without copying a manufacturer P&ID library.
**Покупатель:** Instrumentation, process-control and automation technicians
**Причина покупки:** Feels native to the job and avoids generic electrician/robotics identity.
**Отличие:** A process-loop concept is more specific than generic PLC or robot imagery.
**Визуальное направление:** Original simplified loop/P&ID-inspired diagram with instrument bubbles and signal path
**Создано / обновлено:** 2026-09-23 09:36:02.928333+00 / 2026-09-23 10:09:42.905504+00

Компоненты оценки:
- **buyer_desire**: 8.50 (confidence 0.680). Initial Forge concept score using current occupational terminology, sampled marketplace patterns and technical distinctiveness. No visual has been generated; exact phrases still require IP/common-law screening before promotion. Дата: 2026-09-23 09:36:38.256823+00.
- **clarity_at_glance**: 8.00 (confidence 0.640). Initial Forge concept score using current occupational terminology, sampled marketplace patterns and technical distinctiveness. No visual has been generated; exact phrases still require IP/common-law screening before promotion. Дата: 2026-09-23 09:36:38.256823+00.
- **distinctiveness**: 9.00 (confidence 0.700). Initial Forge concept score using current occupational terminology, sampled marketplace patterns and technical distinctiveness. No visual has been generated; exact phrases still require IP/common-law screening before promotion. Дата: 2026-09-23 09:36:38.256823+00.
- **giftability**: 7.50 (confidence 0.580). Initial Forge concept score using current occupational terminology, sampled marketplace patterns and technical distinctiveness. No visual has been generated; exact phrases still require IP/common-law screening before promotion. Дата: 2026-09-23 09:36:38.256823+00.
- **insider_resonance**: 9.50 (confidence 0.760). Initial Forge concept score using current occupational terminology, sampled marketplace patterns and technical distinctiveness. No visual has been generated; exact phrases still require IP/common-law screening before promotion. Дата: 2026-09-23 09:36:38.256823+00.
- **ip_safety**: 9.00 (confidence 0.680). Initial Forge concept score using current occupational terminology, sampled marketplace patterns and technical distinctiveness. No visual has been generated; exact phrases still require IP/common-law screening before promotion. Дата: 2026-09-23 09:36:38.256823+00.
- **niche_fit**: 9.50 (confidence 0.780). Initial Forge concept score using current occupational terminology, sampled marketplace patterns and technical distinctiveness. No visual has been generated; exact phrases still require IP/common-law screening before promotion. Дата: 2026-09-23 09:36:38.256823+00.
- **visual_potential**: 9.50 (confidence 0.760). Initial Forge concept score using current occupational terminology, sampled marketplace patterns and technical distinctiveness. No visual has been generated; exact phrases still require IP/common-law screening before promotion. Дата: 2026-09-23 09:36:38.256823+00.

#### I&C — sensor / controller / valve
`ic_sensor_controller_valve` · ID `506fb523-fea5-46a0-9c03-da3dcb11c3a5`

**Интерпретация:** Исследовательский кандидат; одобрение владельца не зафиксировано
**Статус БД:** scored · **балл:** 88.72 · **confidence:** 69.17 · **coverage:** 100.00
**Текст / хук:** SENSOR → CONTROLLER → VALVE
**Идея:** I&C — sensor / controller / valve. Core hook: SENSOR → CONTROLLER → VALVE. Process measurement, control loops, field instruments, PLC I/O and fault finding. Execution must stay original and descriptive; avoid employer, OEM, certification-body, association and proprietary-interface branding.
**Покупатель:** Instrumentation and controls technicians
**Причина покупки:** Identity purchase for instrumentation and controls technicians who recognize the real workflow/systems language.
**Отличие:** Insider technical system map direction intended to avoid generic profession-title, retro-badge, skull, flag, coffee and parody templates.
**Визуальное направление:** Minimal closed-loop process-control map using original symbols.
**Создано / обновлено:** 2026-09-23 09:48:50.541446+00 / 2026-09-23 09:55:40.114238+00

Компоненты оценки:
- **buyer_desire**: 8.54 (confidence 0.680). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **clarity_at_glance**: 8.20 (confidence 0.680). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **distinctiveness**: 9.10 (confidence 0.680). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **giftability**: 7.60 (confidence 0.680). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **insider_resonance**: 9.15 (confidence 0.710). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **ip_safety**: 8.80 (confidence 0.680). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **niche_fit**: 9.33 (confidence 0.710). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **visual_potential**: 9.65 (confidence 0.710). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.

#### I&C — what instrument do you play
`v4_ic_instrument_play` · ID `ec845231-ea42-45f3-81d9-f4519a6443fc`

**Интерпретация:** V4: редакционный финалист на выбор владельца, НЕ подтвержденное одобрение
**Статус БД:** shortlisted · **балл:** 92.64 · **confidence:** 70.32 · **coverage:** 100.00
**Текст / хук:** ASKED WHAT INSTRUMENT I PLAY. I SAID 4–20 mA.
**Идея:** Use the recurring outsider misunderstanding of 'instrument technician' as the setup.
**Покупатель:** Instrumentation & controls technicians
**Причина покупки:** Actual joke with outsider setup and insider punchline; highly giftable.
**Отличие:** Technical term functions as a punchline, not a list.
**Визуальное направление:** Concert-poster layout with a process signal replacing a musical waveform.
**Смысл для владельца (источник, EN):** An outsider hears “instrument technician” and thinks musical instrument. The technician answers with “4–20 mA,” treating an industrial current-loop signal as if it were the instrument they play.
**Почему это шутка (источник, EN):** It is a double-meaning joke: “instrument” means one thing to the public and something different in process control. I&C people instantly recognize 4–20 mA, so the punchline doubles as an insider badge.
**Создано / обновлено:** 2026-09-23 19:58:09.189566+00 / 2026-09-24 22:40:42.70901+00

Компоненты оценки:
- **buyer_desire**: 9.40 (confidence 0.700). purchase_trigger_v2 preliminary score; gate passed; trigger=misunderstood_profession_humor Дата: 2026-09-23 19:59:53.152527+00.
- **clarity_at_glance**: 9.30 (confidence 0.760). purchase_trigger_v2 preliminary score; gate passed; trigger=misunderstood_profession_humor Дата: 2026-09-23 19:59:53.152527+00.
- **distinctiveness**: 9.00 (confidence 0.700). purchase_trigger_v2 preliminary score; gate passed; trigger=misunderstood_profession_humor Дата: 2026-09-23 19:59:53.152527+00.
- **giftability**: 9.20 (confidence 0.670). purchase_trigger_v2 preliminary score; gate passed; trigger=misunderstood_profession_humor Дата: 2026-09-23 19:59:53.152527+00.
- **insider_resonance**: 9.60 (confidence 0.720). purchase_trigger_v2 preliminary score; gate passed; trigger=misunderstood_profession_humor Дата: 2026-09-23 19:59:53.152527+00.
- **ip_safety**: 8.70 (confidence 0.600). purchase_trigger_v2 preliminary score; gate passed; trigger=misunderstood_profession_humor Дата: 2026-09-23 19:59:53.152527+00.
- **niche_fit**: 9.50 (confidence 0.720). purchase_trigger_v2 preliminary score; gate passed; trigger=misunderstood_profession_humor Дата: 2026-09-23 19:59:53.152527+00.
- **visual_potential**: 9.00 (confidence 0.720). purchase_trigger_v2 preliminary score; gate passed; trigger=misunderstood_profession_humor Дата: 2026-09-23 19:59:53.152527+00.

#### I&C — control-loop therapist
`v4_ic_loop_therapist` · ID `eefe7e41-9f11-4707-86e4-086ddb24c2d0`

**Интерпретация:** Исследовательский кандидат; одобрение владельца не зафиксировано
**Статус БД:** scored · **балл:** 89.25 · **confidence:** 70.32 · **coverage:** 100.00
**Текст / хук:** CONTROL LOOP THERAPIST.
**Идея:** Anthropomorphize unstable loops as emotional clients needing a calm technician.
**Покупатель:** Instrumentation & controls technicians
**Причина покупки:** Visual absurdity + professional identity, with room for a strong character illustration.
**Отличие:** One technical concept supports a human metaphor; not acronym salad.
**Визуальное направление:** Therapy couch with a wavy process trend as the 'patient.'
**Создано / обновлено:** 2026-09-23 19:58:09.189566+00 / 2026-09-24 05:05:38.621539+00

Компоненты оценки:
- **buyer_desire**: 8.80 (confidence 0.700). purchase_trigger_v2 preliminary score; gate passed; trigger=visual_metaphor Дата: 2026-09-23 19:59:53.152527+00.
- **clarity_at_glance**: 8.90 (confidence 0.760). purchase_trigger_v2 preliminary score; gate passed; trigger=visual_metaphor Дата: 2026-09-23 19:59:53.152527+00.
- **distinctiveness**: 9.10 (confidence 0.700). purchase_trigger_v2 preliminary score; gate passed; trigger=visual_metaphor Дата: 2026-09-23 19:59:53.152527+00.
- **giftability**: 8.50 (confidence 0.670). purchase_trigger_v2 preliminary score; gate passed; trigger=visual_metaphor Дата: 2026-09-23 19:59:53.152527+00.
- **insider_resonance**: 8.90 (confidence 0.720). purchase_trigger_v2 preliminary score; gate passed; trigger=visual_metaphor Дата: 2026-09-23 19:59:53.152527+00.
- **ip_safety**: 8.90 (confidence 0.600). purchase_trigger_v2 preliminary score; gate passed; trigger=visual_metaphor Дата: 2026-09-23 19:59:53.152527+00.
- **niche_fit**: 9.00 (confidence 0.720). purchase_trigger_v2 preliminary score; gate passed; trigger=visual_metaphor Дата: 2026-09-23 19:59:53.152527+00.
- **visual_potential**: 9.40 (confidence 0.720). purchase_trigger_v2 preliminary score; gate passed; trigger=visual_metaphor Дата: 2026-09-23 19:59:53.152527+00.

#### I&C — read the manual
`v4_ic_manual` · ID `1715ba97-871d-4f47-8927-cb8c06ae00dc`

**Интерпретация:** V4: понижен редакционным отбором, сохранен в истории
**Статус БД:** scored · **балл:** 84.59 · **confidence:** 70.32 · **coverage:** 100.00
**Текст / хук:** READ THE MANUAL. THEN CALL ME.
**Идея:** Turn the experienced-tech habit of checking documentation into a knowing joke.
**Покупатель:** Instrumentation & controls technicians
**Причина покупки:** Status + mild frustration, understandable as coworker humor.
**Отличие:** Not a list of calibration steps; it is about avoidable calls.
**Визуальное направление:** Manual/book icon acting as a shield before a phone/pager.
**editorial_reason:** generic technician trope
**Создано / обновлено:** 2026-09-23 19:58:09.189566+00 / 2026-09-24 05:05:38.621539+00

Компоненты оценки:
- **buyer_desire**: 8.30 (confidence 0.700). purchase_trigger_v2 preliminary score; gate passed; trigger=competence_humor Дата: 2026-09-23 19:59:53.152527+00.
- **clarity_at_glance**: 9.10 (confidence 0.760). purchase_trigger_v2 preliminary score; gate passed; trigger=competence_humor Дата: 2026-09-23 19:59:53.152527+00.
- **distinctiveness**: 7.90 (confidence 0.700). purchase_trigger_v2 preliminary score; gate passed; trigger=competence_humor Дата: 2026-09-23 19:59:53.152527+00.
- **giftability**: 8.40 (confidence 0.670). purchase_trigger_v2 preliminary score; gate passed; trigger=competence_humor Дата: 2026-09-23 19:59:53.152527+00.
- **insider_resonance**: 8.80 (confidence 0.720). purchase_trigger_v2 preliminary score; gate passed; trigger=competence_humor Дата: 2026-09-23 19:59:53.152527+00.
- **ip_safety**: 8.90 (confidence 0.600). purchase_trigger_v2 preliminary score; gate passed; trigger=competence_humor Дата: 2026-09-23 19:59:53.152527+00.
- **niche_fit**: 9.10 (confidence 0.720). purchase_trigger_v2 preliminary score; gate passed; trigger=competence_humor Дата: 2026-09-23 19:59:53.152527+00.
- **visual_potential**: 8.30 (confidence 0.720). purchase_trigger_v2 preliminary score; gate passed; trigger=competence_humor Дата: 2026-09-23 19:59:53.152527+00.

#### I&C — blamed instrument, guilty process
`v4_ic_not_transmitter` · ID `f89009e3-7cb4-4187-aea7-1a407937b73e`

**Интерпретация:** Исследовательский кандидат; одобрение владельца не зафиксировано
**Статус БД:** scored · **балл:** 88.05 · **confidence:** 70.32 · **coverage:** 100.00
**Текст / хук:** THE TRANSMITTER IS FINE. YOUR PROCESS IS WEIRD.
**Идея:** The instrument gets blamed first even when the process itself is the problem.
**Покупатель:** Instrumentation & controls technicians
**Причина покупки:** Insider vindication and operations-vs-instrumentation humor.
**Отличие:** It is a social conflict joke, not calibration vocabulary.
**Визуальное направление:** Calm transmitter icon pointing at chaotic process arrows.
**Создано / обновлено:** 2026-09-23 19:58:09.189566+00 / 2026-09-24 05:05:38.621539+00

Компоненты оценки:
- **buyer_desire**: 8.80 (confidence 0.700). purchase_trigger_v2 preliminary score; gate passed; trigger=blame_humor Дата: 2026-09-23 19:59:53.152527+00.
- **clarity_at_glance**: 9.00 (confidence 0.760). purchase_trigger_v2 preliminary score; gate passed; trigger=blame_humor Дата: 2026-09-23 19:59:53.152527+00.
- **distinctiveness**: 8.50 (confidence 0.700). purchase_trigger_v2 preliminary score; gate passed; trigger=blame_humor Дата: 2026-09-23 19:59:53.152527+00.
- **giftability**: 8.60 (confidence 0.670). purchase_trigger_v2 preliminary score; gate passed; trigger=blame_humor Дата: 2026-09-23 19:59:53.152527+00.
- **insider_resonance**: 9.20 (confidence 0.720). purchase_trigger_v2 preliminary score; gate passed; trigger=blame_humor Дата: 2026-09-23 19:59:53.152527+00.
- **ip_safety**: 8.90 (confidence 0.600). purchase_trigger_v2 preliminary score; gate passed; trigger=blame_humor Дата: 2026-09-23 19:59:53.152527+00.
- **niche_fit**: 9.30 (confidence 0.720). purchase_trigger_v2 preliminary score; gate passed; trigger=blame_humor Дата: 2026-09-23 19:59:53.152527+00.
- **visual_potential**: 8.50 (confidence 0.720). purchase_trigger_v2 preliminary score; gate passed; trigger=blame_humor Дата: 2026-09-23 19:59:53.152527+00.

#### I&C — keep the trade mysterious
`v4_ic_trade_mysterious` · ID `93a900a9-b368-411e-86ab-0b821eb0ffc0`

**Интерпретация:** Исследовательский кандидат; одобрение владельца не зафиксировано
**Статус БД:** scored · **балл:** 89.37 · **confidence:** 70.32 · **coverage:** 100.00
**Текст / хук:** INSTRUMENTATION: STILL EXPLAINING MY JOB SINCE DAY ONE.
**Идея:** Identity joke around outsiders not knowing the trade and insiders liking it that way.
**Покупатель:** Instrumentation & controls technicians
**Причина покупки:** Shared obscure-profession identity and giftability.
**Отличие:** The premise is being misunderstood, not listing technical terms.
**Визуальное направление:** Fake dictionary entry crossed out repeatedly with humorous wrong guesses.
**Создано / обновлено:** 2026-09-23 19:58:09.189566+00 / 2026-09-24 05:05:38.621539+00

Компоненты оценки:
- **buyer_desire**: 8.80 (confidence 0.700). purchase_trigger_v2 preliminary score; gate passed; trigger=hidden_tribe_identity Дата: 2026-09-23 19:59:53.152527+00.
- **clarity_at_glance**: 9.10 (confidence 0.760). purchase_trigger_v2 preliminary score; gate passed; trigger=hidden_tribe_identity Дата: 2026-09-23 19:59:53.152527+00.
- **distinctiveness**: 8.70 (confidence 0.700). purchase_trigger_v2 preliminary score; gate passed; trigger=hidden_tribe_identity Дата: 2026-09-23 19:59:53.152527+00.
- **giftability**: 8.90 (confidence 0.670). purchase_trigger_v2 preliminary score; gate passed; trigger=hidden_tribe_identity Дата: 2026-09-23 19:59:53.152527+00.
- **insider_resonance**: 9.40 (confidence 0.720). purchase_trigger_v2 preliminary score; gate passed; trigger=hidden_tribe_identity Дата: 2026-09-23 19:59:53.152527+00.
- **ip_safety**: 8.90 (confidence 0.600). purchase_trigger_v2 preliminary score; gate passed; trigger=hidden_tribe_identity Дата: 2026-09-23 19:59:53.152527+00.
- **niche_fit**: 9.50 (confidence 0.720). purchase_trigger_v2 preliminary score; gate passed; trigger=hidden_tribe_identity Дата: 2026-09-23 19:59:53.152527+00.
- **visual_potential**: 8.70 (confidence 0.720). purchase_trigger_v2 preliminary score; gate passed; trigger=hidden_tribe_identity Дата: 2026-09-23 19:59:53.152527+00.

## 26. Mechatronics Technician
Ключ: `mechatronics_technician` · ID: `26361351-2c9a-4ead-8157-59bc890543ec`

**Статус БД:** scored · **балл:** 75.40 · **confidence:** 63.30 · **coverage:** 100.00
**Аудитория:** Electro-mechanical, mechatronics and robotics maintenance technicians
**Категория:** occupational_identity
**Исследовательская аргументация:** Small occupation but excellent visual/technical language around sensors, pneumatics, robotics, alignment, test and automated machinery. Marketplace evidence is still thin and needs deeper validation.
**Создано / обновлено:** 2026-09-23 09:34:00.70472+00 / 2026-09-23 09:34:30.438105+00

### Компоненты оценки ниши

- **channel_breadth**: 8.00 (confidence 0.600). Initial evidence-weighted Forge score from current BLS/O*NET data, sampled Etsy competition and practitioner-community signals. See niche_candidates.source_notes. This is prioritization research, not a sales forecast. Дата: 2026-09-23 09:34:30.438105+00.
- **competition_opportunity**: 9.00 (confidence 0.500). Initial evidence-weighted Forge score from current BLS/O*NET data, sampled Etsy competition and practitioner-community signals. See niche_candidates.source_notes. This is prioritization research, not a sales forecast. Дата: 2026-09-23 09:34:30.438105+00.
- **concept_depth**: 9.00 (confidence 0.700). Initial evidence-weighted Forge score from current BLS/O*NET data, sampled Etsy competition and practitioner-community signals. See niche_candidates.source_notes. This is prioritization research, not a sales forecast. Дата: 2026-09-23 09:34:30.438105+00.
- **demand_evidence**: 6.00 (confidence 0.800). Initial evidence-weighted Forge score from current BLS/O*NET data, sampled Etsy competition and practitioner-community signals. See niche_candidates.source_notes. This is prioritization research, not a sales forecast. Дата: 2026-09-23 09:34:30.438105+00.
- **founder_edge**: 2.00 (confidence 0.400). Initial evidence-weighted Forge score from current BLS/O*NET data, sampled Etsy competition and practitioner-community signals. See niche_candidates.source_notes. This is prioritization research, not a sales forecast. Дата: 2026-09-23 09:34:30.438105+00.
- **identity_intensity**: 6.80 (confidence 0.550). Initial evidence-weighted Forge score from current BLS/O*NET data, sampled Etsy competition and practitioner-community signals. See niche_candidates.source_notes. This is prioritization research, not a sales forecast. Дата: 2026-09-23 09:34:30.438105+00.
- **legal_safety**: 9.00 (confidence 0.700). Initial evidence-weighted Forge score from current BLS/O*NET data, sampled Etsy competition and practitioner-community signals. See niche_candidates.source_notes. This is prioritization research, not a sales forecast. Дата: 2026-09-23 09:34:30.438105+00.
- **purchase_motivation**: 6.80 (confidence 0.550). Initial evidence-weighted Forge score from current BLS/O*NET data, sampled Etsy competition and practitioner-community signals. See niche_candidates.source_notes. This is prioritization research, not a sales forecast. Дата: 2026-09-23 09:34:30.438105+00.
- **repeatability**: 8.00 (confidence 0.600). Initial evidence-weighted Forge score from current BLS/O*NET data, sampled Etsy competition and practitioner-community signals. See niche_candidates.source_notes. This is prioritization research, not a sales forecast. Дата: 2026-09-23 09:34:30.438105+00.
- **visual_language**: 9.50 (confidence 0.750). Initial evidence-weighted Forge score from current BLS/O*NET data, sampled Etsy competition and practitioner-community signals. See niche_candidates.source_notes. This is prioritization research, not a sales forecast. Дата: 2026-09-23 09:34:30.438105+00.

### Концепции (0)

## 27. Medical Dosimetrist
Ключ: `medical_dosimetrist` · ID: `531254b3-5bb6-48bc-89f0-5810186b7e6f`

**Статус БД:** scored · **балл:** 72.95 · **confidence:** 78.18 · **coverage:** 100.00
**Аудитория:** Certified medical dosimetrists and radiation-treatment planning teams
**Категория:** occupational_identity
**Исследовательская аргументация:** Very small but high-skill, highly paid profession with strong technical identity around dose, beams, planning, fractions and treatment geometry. Etsy has about 46–48 dedicated items, so demand is small but identity and concept specificity are unusually strong.
**Создано / обновлено:** 2026-09-23 09:42:54.27545+00 / 2026-09-23 09:43:36.792084+00

### Компоненты оценки ниши

- **channel_breadth**: 7.00 (confidence 0.580). Forge hidden-trades v2 initial score using current BLS/O*NET occupational evidence plus sampled Etsy marketplace depth. Scores prioritize buyer identity and whitespace, not raw occupation size. Benchmark niches intentionally receive competition penalties. Дата: 2026-09-23 09:43:36.792084+00.
- **competition_opportunity**: 6.00 (confidence 0.840). Forge hidden-trades v2 initial score using current BLS/O*NET occupational evidence plus sampled Etsy marketplace depth. Scores prioritize buyer identity and whitespace, not raw occupation size. Benchmark niches intentionally receive competition penalties. Дата: 2026-09-23 09:43:36.792084+00.
- **concept_depth**: 9.50 (confidence 0.820). Forge hidden-trades v2 initial score using current BLS/O*NET occupational evidence plus sampled Etsy marketplace depth. Scores prioritize buyer identity and whitespace, not raw occupation size. Benchmark niches intentionally receive competition penalties. Дата: 2026-09-23 09:43:36.792084+00.
- **demand_evidence**: 4.50 (confidence 0.880). Forge hidden-trades v2 initial score using current BLS/O*NET occupational evidence plus sampled Etsy marketplace depth. Scores prioritize buyer identity and whitespace, not raw occupation size. Benchmark niches intentionally receive competition penalties. Дата: 2026-09-23 09:43:36.792084+00.
- **founder_edge**: 2.00 (confidence 0.400). Forge hidden-trades v2 initial score using current BLS/O*NET occupational evidence plus sampled Etsy marketplace depth. Scores prioritize buyer identity and whitespace, not raw occupation size. Benchmark niches intentionally receive competition penalties. Дата: 2026-09-23 09:43:36.792084+00.
- **identity_intensity**: 9.00 (confidence 0.780). Forge hidden-trades v2 initial score using current BLS/O*NET occupational evidence plus sampled Etsy marketplace depth. Scores prioritize buyer identity and whitespace, not raw occupation size. Benchmark niches intentionally receive competition penalties. Дата: 2026-09-23 09:43:36.792084+00.
- **legal_safety**: 8.50 (confidence 0.640). Forge hidden-trades v2 initial score using current BLS/O*NET occupational evidence plus sampled Etsy marketplace depth. Scores prioritize buyer identity and whitespace, not raw occupation size. Benchmark niches intentionally receive competition penalties. Дата: 2026-09-23 09:43:36.792084+00.
- **purchase_motivation**: 8.00 (confidence 0.720). Forge hidden-trades v2 initial score using current BLS/O*NET occupational evidence plus sampled Etsy marketplace depth. Scores prioritize buyer identity and whitespace, not raw occupation size. Benchmark niches intentionally receive competition penalties. Дата: 2026-09-23 09:43:36.792084+00.
- **repeatability**: 8.00 (confidence 0.660). Forge hidden-trades v2 initial score using current BLS/O*NET occupational evidence plus sampled Etsy marketplace depth. Scores prioritize buyer identity and whitespace, not raw occupation size. Benchmark niches intentionally receive competition penalties. Дата: 2026-09-23 09:43:36.792084+00.
- **visual_language**: 9.50 (confidence 0.840). Forge hidden-trades v2 initial score using current BLS/O*NET occupational evidence plus sampled Etsy marketplace depth. Scores prioritize buyer identity and whitespace, not raw occupation size. Benchmark niches intentionally receive competition penalties. Дата: 2026-09-23 09:43:36.792084+00.

### Концепции (0)

## 28. Medical Laboratory Scientist / CLS
Ключ: `medical_laboratory_scientist` · ID: `b25ef37f-c96d-441e-bd69-83ae149c66f9`

**Статус БД:** scored · **балл:** 75.95 · **confidence:** 81.74 · **coverage:** 100.00
**Аудитория:** Medical laboratory scientists, clinical laboratory scientists and technologists
**Категория:** occupational_identity
**Исследовательская аргументация:** Large replacement-driven healthcare occupation with broad specialty depth but a mature merch market. Retain as benchmark and potential specialty-splitting source rather than treating generic MLS as whitespace.
**Создано / обновлено:** 2026-09-23 09:42:54.27545+00 / 2026-09-23 09:43:36.792084+00

### Компоненты оценки ниши

- **channel_breadth**: 8.00 (confidence 0.680). Forge hidden-trades v2 initial score using current BLS/O*NET occupational evidence plus sampled Etsy marketplace depth. Scores prioritize buyer identity and whitespace, not raw occupation size. Benchmark niches intentionally receive competition penalties. Дата: 2026-09-23 09:43:36.792084+00.
- **competition_opportunity**: 2.00 (confidence 0.940). Forge hidden-trades v2 initial score using current BLS/O*NET occupational evidence plus sampled Etsy marketplace depth. Scores prioritize buyer identity and whitespace, not raw occupation size. Benchmark niches intentionally receive competition penalties. Дата: 2026-09-23 09:43:36.792084+00.
- **concept_depth**: 9.00 (confidence 0.780). Forge hidden-trades v2 initial score using current BLS/O*NET occupational evidence plus sampled Etsy marketplace depth. Scores prioritize buyer identity and whitespace, not raw occupation size. Benchmark niches intentionally receive competition penalties. Дата: 2026-09-23 09:43:36.792084+00.
- **demand_evidence**: 9.00 (confidence 0.940). Forge hidden-trades v2 initial score using current BLS/O*NET occupational evidence plus sampled Etsy marketplace depth. Scores prioritize buyer identity and whitespace, not raw occupation size. Benchmark niches intentionally receive competition penalties. Дата: 2026-09-23 09:43:36.792084+00.
- **founder_edge**: 2.00 (confidence 0.400). Forge hidden-trades v2 initial score using current BLS/O*NET occupational evidence plus sampled Etsy marketplace depth. Scores prioritize buyer identity and whitespace, not raw occupation size. Benchmark niches intentionally receive competition penalties. Дата: 2026-09-23 09:43:36.792084+00.
- **identity_intensity**: 8.50 (confidence 0.780). Forge hidden-trades v2 initial score using current BLS/O*NET occupational evidence plus sampled Etsy marketplace depth. Scores prioritize buyer identity and whitespace, not raw occupation size. Benchmark niches intentionally receive competition penalties. Дата: 2026-09-23 09:43:36.792084+00.
- **legal_safety**: 8.50 (confidence 0.660). Forge hidden-trades v2 initial score using current BLS/O*NET occupational evidence plus sampled Etsy marketplace depth. Scores prioritize buyer identity and whitespace, not raw occupation size. Benchmark niches intentionally receive competition penalties. Дата: 2026-09-23 09:43:36.792084+00.
- **purchase_motivation**: 8.50 (confidence 0.760). Forge hidden-trades v2 initial score using current BLS/O*NET occupational evidence plus sampled Etsy marketplace depth. Scores prioritize buyer identity and whitespace, not raw occupation size. Benchmark niches intentionally receive competition penalties. Дата: 2026-09-23 09:43:36.792084+00.
- **repeatability**: 9.00 (confidence 0.760). Forge hidden-trades v2 initial score using current BLS/O*NET occupational evidence plus sampled Etsy marketplace depth. Scores prioritize buyer identity and whitespace, not raw occupation size. Benchmark niches intentionally receive competition penalties. Дата: 2026-09-23 09:43:36.792084+00.
- **visual_language**: 9.00 (confidence 0.800). Forge hidden-trades v2 initial score using current BLS/O*NET occupational evidence plus sampled Etsy marketplace depth. Scores prioritize buyer identity and whitespace, not raw occupation size. Benchmark niches intentionally receive competition penalties. Дата: 2026-09-23 09:43:36.792084+00.

### Концепции (0)

## 29. Neurodiagnostic / EEG Technologist
Ключ: `neurodiagnostic_technologist` · ID: `f98e08b7-fb25-4cf9-bd14-4c425382509a`

**Статус БД:** scored · **балл:** 76.85 · **confidence:** 72.98 · **coverage:** 100.00
**Аудитория:** EEG, END, IONM and neurodiagnostic technologists
**Категория:** occupational_identity
**Исследовательская аргументация:** High-insider specialty with authentic terminology around electrodes, impedance, 10–20 placement, artifact recognition, EEG waves and IONM. Etsy already has 60+ neurodiagnostic items including unusually specific insider jokes, so this is a quality/differentiation challenge rather than empty whitespace.
**Создано / обновлено:** 2026-09-23 09:42:54.27545+00 / 2026-09-23 09:43:36.792084+00

### Компоненты оценки ниши

- **channel_breadth**: 7.00 (confidence 0.600). Forge hidden-trades v2 initial score using current BLS/O*NET occupational evidence plus sampled Etsy marketplace depth. Scores prioritize buyer identity and whitespace, not raw occupation size. Benchmark niches intentionally receive competition penalties. Дата: 2026-09-23 09:43:36.792084+00.
- **competition_opportunity**: 5.50 (confidence 0.820). Forge hidden-trades v2 initial score using current BLS/O*NET occupational evidence plus sampled Etsy marketplace depth. Scores prioritize buyer identity and whitespace, not raw occupation size. Benchmark niches intentionally receive competition penalties. Дата: 2026-09-23 09:43:36.792084+00.
- **concept_depth**: 9.50 (confidence 0.840). Forge hidden-trades v2 initial score using current BLS/O*NET occupational evidence plus sampled Etsy marketplace depth. Scores prioritize buyer identity and whitespace, not raw occupation size. Benchmark niches intentionally receive competition penalties. Дата: 2026-09-23 09:43:36.792084+00.
- **demand_evidence**: 6.50 (confidence 0.580). Forge hidden-trades v2 initial score using current BLS/O*NET occupational evidence plus sampled Etsy marketplace depth. Scores prioritize buyer identity and whitespace, not raw occupation size. Benchmark niches intentionally receive competition penalties. Дата: 2026-09-23 09:43:36.792084+00.
- **founder_edge**: 2.00 (confidence 0.400). Forge hidden-trades v2 initial score using current BLS/O*NET occupational evidence plus sampled Etsy marketplace depth. Scores prioritize buyer identity and whitespace, not raw occupation size. Benchmark niches intentionally receive competition penalties. Дата: 2026-09-23 09:43:36.792084+00.
- **identity_intensity**: 9.00 (confidence 0.800). Forge hidden-trades v2 initial score using current BLS/O*NET occupational evidence plus sampled Etsy marketplace depth. Scores prioritize buyer identity and whitespace, not raw occupation size. Benchmark niches intentionally receive competition penalties. Дата: 2026-09-23 09:43:36.792084+00.
- **legal_safety**: 8.50 (confidence 0.640). Forge hidden-trades v2 initial score using current BLS/O*NET occupational evidence plus sampled Etsy marketplace depth. Scores prioritize buyer identity and whitespace, not raw occupation size. Benchmark niches intentionally receive competition penalties. Дата: 2026-09-23 09:43:36.792084+00.
- **purchase_motivation**: 8.00 (confidence 0.720). Forge hidden-trades v2 initial score using current BLS/O*NET occupational evidence plus sampled Etsy marketplace depth. Scores prioritize buyer identity and whitespace, not raw occupation size. Benchmark niches intentionally receive competition penalties. Дата: 2026-09-23 09:43:36.792084+00.
- **repeatability**: 8.50 (confidence 0.720). Forge hidden-trades v2 initial score using current BLS/O*NET occupational evidence plus sampled Etsy marketplace depth. Scores prioritize buyer identity and whitespace, not raw occupation size. Benchmark niches intentionally receive competition penalties. Дата: 2026-09-23 09:43:36.792084+00.
- **visual_language**: 10.00 (confidence 0.860). Forge hidden-trades v2 initial score using current BLS/O*NET occupational evidence plus sampled Etsy marketplace depth. Scores prioritize buyer identity and whitespace, not raw occupation size. Benchmark niches intentionally receive competition penalties. Дата: 2026-09-23 09:43:36.792084+00.

### Концепции (0)

## 30. Nondestructive Testing (NDT/NDE) Technician
Ключ: `nondestructive_testing_technician` · ID: `b1e293dc-286d-40b5-944e-fb4201594c8c`

**Статус БД:** scored · **балл:** 78.50 · **confidence:** 73.11 · **coverage:** 100.00
**Аудитория:** NDT/NDE technicians working across UT, RT, MT, PT, VT and advanced inspection methods
**Категория:** occupational_identity
**Исследовательская аргументация:** High insider-language depth and certification/method identity; strong visual potential from waveforms, weld inspection and method families. Direct BLS sizing is not clean, so this is a high-upside / medium-confidence research candidate.
**Создано / обновлено:** 2026-09-23 09:34:00.70472+00 / 2026-09-23 10:14:18.633101+00

### Компоненты оценки ниши

- **channel_breadth**: 7.00 (confidence 0.660). Initial evidence-weighted Forge score from current BLS/O*NET data, sampled Etsy competition and practitioner-community signals. See niche_candidates.source_notes. This is prioritization research, not a sales forecast. ASNT describes NDT across infrastructure, manufacturing and industrial systems; confidence in cross-channel/cross-industry applicability improved. Дата: 2026-09-23 09:34:30.438105+00.
- **competition_opportunity**: 8.80 (confidence 0.780). Initial evidence-weighted Forge score from current BLS/O*NET data, sampled Etsy competition and practitioner-community signals. See niche_candidates.source_notes. This is prioritization research, not a sales forecast. Current Etsy NDT Inspector Gift page showed only 6 relevant results, with a small cluster of NDT-tech humor shirts; confidence in relatively thin direct merch competition is materially higher. Дата: 2026-09-23 09:34:30.438105+00.
- **concept_depth**: 9.50 (confidence 0.820). Initial evidence-weighted Forge score from current BLS/O*NET data, sampled Etsy competition and practitioner-community signals. See niche_candidates.source_notes. This is prioritization research, not a sales forecast. ASNT career/method structure and practitioners confirm multiple materially distinct method families and advancement paths: UT, PAUT, RT, MT, PT, VT and interpretation/reporting. Дата: 2026-09-23 09:34:30.438105+00.
- **demand_evidence**: 6.00 (confidence 0.620). Initial evidence-weighted Forge score from current BLS/O*NET data, sampled Etsy competition and practitioner-community signals. See niche_candidates.source_notes. This is prioritization research, not a sales forecast. ASNT current career resources and Aug 2026 job postings confirm active hiring and a real career ladder, but there is still no clean standalone BLS occupation-size series; demand confidence remains moderate. Дата: 2026-09-23 09:34:30.438105+00.
- **founder_edge**: 2.00 (confidence 0.400). Initial evidence-weighted Forge score from current BLS/O*NET data, sampled Etsy competition and practitioner-community signals. See niche_candidates.source_notes. This is prioritization research, not a sales forecast. Дата: 2026-09-23 09:34:30.438105+00.
- **identity_intensity**: 8.50 (confidence 0.820). Initial evidence-weighted Forge score from current BLS/O*NET data, sampled Etsy competition and practitioner-community signals. See niche_candidates.source_notes. This is prioritization research, not a sales forecast. ASNT method/certification ladder plus active 2026 NDT practitioner discussions strongly support a distinct professional identity. Дата: 2026-09-23 09:34:30.438105+00.
- **legal_safety**: 8.00 (confidence 0.450). Initial evidence-weighted Forge score from current BLS/O*NET data, sampled Etsy competition and practitioner-community signals. See niche_candidates.source_notes. This is prioritization research, not a sales forecast. Дата: 2026-09-23 09:34:30.438105+00.
- **purchase_motivation**: 7.50 (confidence 0.740). Initial evidence-weighted Forge score from current BLS/O*NET data, sampled Etsy competition and practitioner-community signals. See niche_candidates.source_notes. This is prioritization research, not a sales forecast. Method certifications, Level II/III progression and strong practitioner identity improve confidence in niche-pride/gift motivation; still not direct sales evidence. Дата: 2026-09-23 09:34:30.438105+00.
- **repeatability**: 8.00 (confidence 0.720). Initial evidence-weighted Forge score from current BLS/O*NET data, sampled Etsy competition and practitioner-community signals. See niche_candidates.source_notes. This is prioritization research, not a sales forecast. Multiple methods/certification levels support a broad series rather than one generic NDT design. Дата: 2026-09-23 09:34:30.438105+00.
- **visual_language**: 9.50 (confidence 0.840). Initial evidence-weighted Forge score from current BLS/O*NET data, sampled Etsy competition and practitioner-community signals. See niche_candidates.source_notes. This is prioritization research, not a sales forecast. Current NDT methods and practitioner evidence strongly support method-specific waveforms, indication maps, radiography, probe/weld geometry and inspection/reporting cues. Дата: 2026-09-23 09:34:30.438105+00.

### Концепции (9)

#### NDT — indication to evaluation
`ndt_indication_evaluate_report` · ID `f7c34150-cb10-46db-9450-5e4f4183796c`

**Интерпретация:** Исследовательский кандидат; одобрение владельца не зафиксировано
**Статус БД:** scored · **балл:** 85.46 · **confidence:** 64.84 · **coverage:** 100.00
**Текст / хук:** INDICATION → EVALUATE → REPORT
**Идея:** NDT TECHNICIAN workflow: INDICATION → EVALUATE → REPORT, emphasizing the difference between detecting an indication and professionally evaluating/reporting it. Use generic inspection marks and report-grid elements.
**Покупатель:** NDT/NDE inspectors and technicians
**Причина покупки:** Professional judgment is central to NDT identity and distinguishes technicians from simple equipment operators.
**Отличие:** Concept focuses on interpretation/evaluation rather than common hard-hat/welder imagery.
**Визуальное направление:** Inspection callout leading to evaluation grid and report stamp-like geometry, but no official seals
**Создано / обновлено:** 2026-09-23 09:36:02.928333+00 / 2026-09-23 10:09:42.905504+00

Компоненты оценки:
- **buyer_desire**: 7.80 (confidence 0.580). Initial Forge concept score using current occupational terminology, sampled marketplace patterns and technical distinctiveness. No visual has been generated; exact phrases still require IP/common-law screening before promotion. Дата: 2026-09-23 09:36:38.256823+00.
- **clarity_at_glance**: 8.50 (confidence 0.640). Initial Forge concept score using current occupational terminology, sampled marketplace patterns and technical distinctiveness. No visual has been generated; exact phrases still require IP/common-law screening before promotion. Дата: 2026-09-23 09:36:38.256823+00.
- **distinctiveness**: 9.00 (confidence 0.660). Initial Forge concept score using current occupational terminology, sampled marketplace patterns and technical distinctiveness. No visual has been generated; exact phrases still require IP/common-law screening before promotion. Дата: 2026-09-23 09:36:38.256823+00.
- **giftability**: 7.00 (confidence 0.540). Initial Forge concept score using current occupational terminology, sampled marketplace patterns and technical distinctiveness. No visual has been generated; exact phrases still require IP/common-law screening before promotion. Дата: 2026-09-23 09:36:38.256823+00.
- **insider_resonance**: 9.50 (confidence 0.760). Initial Forge concept score using current occupational terminology, sampled marketplace patterns and technical distinctiveness. No visual has been generated; exact phrases still require IP/common-law screening before promotion. Дата: 2026-09-23 09:36:38.256823+00.
- **ip_safety**: 9.50 (confidence 0.700). Initial Forge concept score using current occupational terminology, sampled marketplace patterns and technical distinctiveness. No visual has been generated; exact phrases still require IP/common-law screening before promotion. Дата: 2026-09-23 09:36:38.256823+00.
- **niche_fit**: 9.50 (confidence 0.780). Initial Forge concept score using current occupational terminology, sampled marketplace patterns and technical distinctiveness. No visual has been generated; exact phrases still require IP/common-law screening before promotion. Дата: 2026-09-23 09:36:38.256823+00.
- **visual_potential**: 8.00 (confidence 0.580). Initial Forge concept score using current occupational terminology, sampled marketplace patterns and technical distinctiveness. No visual has been generated; exact phrases still require IP/common-law screening before promotion. Дата: 2026-09-23 09:36:38.256823+00.

#### NDT — method matrix
`ndt_method_matrix_vt_pt_mt_ut_rt` · ID `71d8d28c-e337-4bd7-9da7-caaae2f3b745`

**Интерпретация:** Исследовательский кандидат; одобрение владельца не зафиксировано
**Статус БД:** scored · **балл:** 87.10 · **confidence:** 71.72 · **coverage:** 100.00
**Текст / хук:** VT • PT • MT • UT • RT
**Идея:** NDT / NDE TECHNICIAN identity organized around VT • PT • MT • UT • RT, the core inspection-method family. Use original symbols for eye/visual, penetrant, magnetic field, ultrasonic waveform and radiographic image rather than certification logos.
**Покупатель:** NDT/NDE technicians and inspectors
**Причина покупки:** Method certifications are part of how technicians identify and specialize.
**Отличие:** A method matrix is more insider-specific than generic welding or inspection merch.
**Визуальное направление:** Five-method technical matrix with distinct original symbols and one cohesive industrial grid
**Создано / обновлено:** 2026-09-23 09:36:02.928333+00 / 2026-09-23 10:09:42.905504+00

Компоненты оценки:
- **buyer_desire**: 8.00 (confidence 0.620). Initial Forge concept score using current occupational terminology, sampled marketplace patterns and technical distinctiveness. No visual has been generated; exact phrases still require IP/common-law screening before promotion. Дата: 2026-09-23 09:36:38.256823+00.
- **clarity_at_glance**: 8.50 (confidence 0.660). Initial Forge concept score using current occupational terminology, sampled marketplace patterns and technical distinctiveness. No visual has been generated; exact phrases still require IP/common-law screening before promotion. Дата: 2026-09-23 09:36:38.256823+00.
- **distinctiveness**: 7.50 (confidence 0.780). Method abbreviations VT/PT/MT/UT/RT are authentic, widely used NDT vocabulary and were also found together in a current non-apparel welding inspection spreadsheet. That supports insider resonance but reduces phrase distinctiveness; no exact merch collision was found in the sampled Etsy-focused search. Дата: 2026-09-23 09:36:38.256823+00.
- **giftability**: 8.00 (confidence 0.620). Initial Forge concept score using current occupational terminology, sampled marketplace patterns and technical distinctiveness. No visual has been generated; exact phrases still require IP/common-law screening before promotion. Дата: 2026-09-23 09:36:38.256823+00.
- **insider_resonance**: 10.00 (confidence 0.800). Initial Forge concept score using current occupational terminology, sampled marketplace patterns and technical distinctiveness. No visual has been generated; exact phrases still require IP/common-law screening before promotion. Дата: 2026-09-23 09:36:38.256823+00.
- **ip_safety**: 9.00 (confidence 0.660). Initial Forge concept score using current occupational terminology, sampled marketplace patterns and technical distinctiveness. No visual has been generated; exact phrases still require IP/common-law screening before promotion. Дата: 2026-09-23 09:36:38.256823+00.
- **niche_fit**: 10.00 (confidence 0.820). Initial Forge concept score using current occupational terminology, sampled marketplace patterns and technical distinctiveness. No visual has been generated; exact phrases still require IP/common-law screening before promotion. Дата: 2026-09-23 09:36:38.256823+00.
- **visual_potential**: 9.50 (confidence 0.740). Initial Forge concept score using current occupational terminology, sampled marketplace patterns and technical distinctiveness. No visual has been generated; exact phrases still require IP/common-law screening before promotion. Дата: 2026-09-23 09:36:38.256823+00.

#### NDT — magnetic particle evaluation
`ndt_mt_field_indication_evaluate` · ID `bbe49cf1-ea63-4055-90bf-8891354c2d79`

**Интерпретация:** Исследовательский кандидат; одобрение владельца не зафиксировано
**Статус БД:** scored · **балл:** 88.03 · **confidence:** 68.17 · **coverage:** 100.00
**Текст / хук:** FIELD • INDICATION • EVALUATE
**Идея:** NDT — magnetic particle evaluation. Core hook: FIELD • INDICATION • EVALUATE. Inspection-method identity, indication evaluation and technical interpretation. Execution must stay original and descriptive; avoid employer, OEM, certification-body, association and proprietary-interface branding.
**Покупатель:** NDT/NDE technicians and inspectors
**Причина покупки:** Identity purchase for ndt/nde technicians and inspectors who recognize the real workflow/systems language.
**Отличие:** Insider technical technical map direction intended to avoid generic profession-title, retro-badge, skull, flag, coffee and parody templates.
**Визуальное направление:** Magnetic-field and indication geometry for MT identity; no equipment-brand imagery.
**Создано / обновлено:** 2026-09-23 09:48:50.541446+00 / 2026-09-23 09:55:40.114238+00

Компоненты оценки:
- **buyer_desire**: 8.31 (confidence 0.670). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **clarity_at_glance**: 7.77 (confidence 0.670). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **distinctiveness**: 9.20 (confidence 0.670). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **giftability**: 7.47 (confidence 0.670). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **insider_resonance**: 9.30 (confidence 0.700). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **ip_safety**: 8.60 (confidence 0.670). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **niche_fit**: 9.31 (confidence 0.700). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **visual_potential**: 9.60 (confidence 0.700). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.

#### NDT — phased-array sector scan
`ndt_paut_sector_scan_map` · ID `5955d789-58d6-49e0-8b1a-6039e9d3edeb`

**Интерпретация:** Исследовательский кандидат; одобрение владельца не зафиксировано
**Статус БД:** scored · **балл:** 88.64 · **confidence:** 68.17 · **coverage:** 100.00
**Текст / хук:** SECTOR • SCAN • MAP
**Идея:** NDT — phased-array sector scan. Core hook: SECTOR • SCAN • MAP. Inspection-method identity, indication evaluation and technical interpretation. Execution must stay original and descriptive; avoid employer, OEM, certification-body, association and proprietary-interface branding.
**Покупатель:** NDT/NDE technicians and inspectors
**Причина покупки:** Identity purchase for ndt/nde technicians and inspectors who recognize the real workflow/systems language.
**Отличие:** Insider technical technical map direction intended to avoid generic profession-title, retro-badge, skull, flag, coffee and parody templates.
**Визуальное направление:** Advanced UT/PAUT visual using an original sector-scan fan and indication map; no copied instrument UI.
**Создано / обновлено:** 2026-09-23 09:48:50.541446+00 / 2026-09-23 09:55:40.114238+00

Компоненты оценки:
- **buyer_desire**: 8.41 (confidence 0.670). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **clarity_at_glance**: 7.80 (confidence 0.670). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **distinctiveness**: 9.30 (confidence 0.670). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **giftability**: 7.50 (confidence 0.670). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **insider_resonance**: 9.35 (confidence 0.700). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **ip_safety**: 8.60 (confidence 0.670). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **niche_fit**: 9.31 (confidence 0.700). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **visual_potential**: 9.65 (confidence 0.700). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.

#### NDT — penetrant indication
`ndt_pt_process_indication` · ID `ca25eafb-9dc0-436b-8581-f5bb72f552de`

**Интерпретация:** Исследовательский кандидат; одобрение владельца не зафиксировано
**Статус БД:** scored · **балл:** 86.39 · **confidence:** 68.17 · **coverage:** 100.00
**Текст / хук:** PREP • APPLY • REMOVE • INSPECT
**Идея:** NDT — penetrant indication. Core hook: PREP • APPLY • REMOVE • INSPECT. Inspection-method identity, indication evaluation and technical interpretation. Execution must stay original and descriptive; avoid employer, OEM, certification-body, association and proprietary-interface branding.
**Покупатель:** NDT/NDE technicians and inspectors
**Причина покупки:** Identity purchase for ndt/nde technicians and inspectors who recognize the real workflow/systems language.
**Отличие:** Insider technical process direction intended to avoid generic profession-title, retro-badge, skull, flag, coffee and parody templates.
**Визуальное направление:** High-level penetrant-testing identity sequence with original surface/indication visuals; no procedural times or chemical instructions.
**Создано / обновлено:** 2026-09-23 09:48:50.541446+00 / 2026-09-23 09:55:40.114238+00

Компоненты оценки:
- **buyer_desire**: 8.21 (confidence 0.670). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **clarity_at_glance**: 8.73 (confidence 0.670). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **distinctiveness**: 8.60 (confidence 0.670). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **giftability**: 7.83 (confidence 0.670). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **insider_resonance**: 9.05 (confidence 0.700). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **ip_safety**: 8.80 (confidence 0.670). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **niche_fit**: 9.31 (confidence 0.700). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **visual_potential**: 8.85 (confidence 0.700). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.

#### NDT — radiographic interpretation
`ndt_rt_image_interpret_report` · ID `e514dd02-68f6-43b8-afeb-98fb6212fd73`

**Интерпретация:** Исследовательский кандидат; одобрение владельца не зафиксировано
**Статус БД:** scored · **балл:** 88.61 · **confidence:** 69.17 · **coverage:** 100.00
**Текст / хук:** IMAGE • INTERPRET • REPORT
**Идея:** NDT — radiographic interpretation. Core hook: IMAGE • INTERPRET • REPORT. Inspection-method identity, indication evaluation and technical interpretation. Execution must stay original and descriptive; avoid employer, OEM, certification-body, association and proprietary-interface branding.
**Покупатель:** NDT/NDE technicians and inspectors
**Причина покупки:** Identity purchase for ndt/nde technicians and inspectors who recognize the real workflow/systems language.
**Отличие:** Insider technical diagnostic direction intended to avoid generic profession-title, retro-badge, skull, flag, coffee and parody templates.
**Визуальное направление:** Radiographic-image interpretation identity using abstract film/digital image geometry; no source-handling instructions.
**Создано / обновлено:** 2026-09-23 09:48:50.541446+00 / 2026-09-23 09:55:40.114238+00

Компоненты оценки:
- **buyer_desire**: 8.61 (confidence 0.680). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **clarity_at_glance**: 8.57 (confidence 0.680). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **distinctiveness**: 9.00 (confidence 0.680). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **giftability**: 7.87 (confidence 0.680). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **insider_resonance**: 9.40 (confidence 0.710). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **ip_safety**: 8.70 (confidence 0.680). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **niche_fit**: 9.41 (confidence 0.710). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **visual_potential**: 8.90 (confidence 0.710). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.

#### NDT — surface / volume methods
`ndt_surface_volume_method_map` · ID `d074f09d-9aff-45be-9814-c7bc14687f09`

**Интерпретация:** Исследовательский кандидат; одобрение владельца не зафиксировано
**Статус БД:** scored · **балл:** 88.03 · **confidence:** 69.17 · **coverage:** 100.00
**Текст / хук:** SURFACE ↔ VOLUME
**Идея:** NDT — surface / volume methods. Core hook: SURFACE ↔ VOLUME. Inspection-method identity, indication evaluation and technical interpretation. Execution must stay original and descriptive; avoid employer, OEM, certification-body, association and proprietary-interface branding.
**Покупатель:** NDT/NDE technicians and inspectors
**Причина покупки:** Identity purchase for ndt/nde technicians and inspectors who recognize the real workflow/systems language.
**Отличие:** Insider technical system map direction intended to avoid generic profession-title, retro-badge, skull, flag, coffee and parody templates.
**Визуальное направление:** Method-selection identity contrasting surface and volumetric inspection with original VT/PT/MT vs UT/RT-style symbol groups.
**Создано / обновлено:** 2026-09-23 09:48:50.541446+00 / 2026-09-23 09:55:40.114238+00

Компоненты оценки:
- **buyer_desire**: 8.41 (confidence 0.680). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **clarity_at_glance**: 8.17 (confidence 0.680). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **distinctiveness**: 9.00 (confidence 0.680). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **giftability**: 7.57 (confidence 0.680). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **insider_resonance**: 9.10 (confidence 0.710). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **ip_safety**: 8.80 (confidence 0.680). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **niche_fit**: 9.31 (confidence 0.710). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **visual_potential**: 9.60 (confidence 0.710). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.

#### NDT — ultrasonic A-scan
`ndt_ultrasonic_calibrate_scan_interpret_record` · ID `23c8a431-acfb-4d45-a93a-2d70318ba406`

**Интерпретация:** Исследовательский кандидат; одобрение владельца не зафиксировано
**Статус БД:** scored · **балл:** 91.70 · **confidence:** 71.64 · **coverage:** 100.00
**Текст / хук:** CALIBRATE • SCAN • INTERPRET • RECORD
**Идея:** ULTRASONIC TESTING / NDT TECHNICIAN concept using CALIBRATE • SCAN • INTERPRET • RECORD around an original A-scan-style waveform and generic probe/weld geometry. No copied instrument UI.
**Покупатель:** Ultrasonic NDT technicians / Level II inspectors
**Причина покупки:** Deep method-specific identity for a technically demanding NDT specialty.
**Отличие:** Far more specialized than generic NDT text and visually distinct through the waveform/inspection geometry.
**Визуальное направление:** Original A-scan waveform, probe beam path and weld cross-section abstraction
**Создано / обновлено:** 2026-09-23 09:36:02.928333+00 / 2026-09-23 10:15:01.390702+00

Компоненты оценки:
- **buyer_desire**: 8.50 (confidence 0.640). Initial Forge concept score using current occupational terminology, sampled marketplace patterns and technical distinctiveness. No visual has been generated; exact phrases still require IP/common-law screening before promotion. Дата: 2026-09-23 09:36:38.256823+00.
- **clarity_at_glance**: 8.00 (confidence 0.620). Initial Forge concept score using current occupational terminology, sampled marketplace patterns and technical distinctiveness. No visual has been generated; exact phrases still require IP/common-law screening before promotion. Дата: 2026-09-23 09:36:38.256823+00.
- **distinctiveness**: 9.50 (confidence 0.720). Initial Forge concept score using current occupational terminology, sampled marketplace patterns and technical distinctiveness. No visual has been generated; exact phrases still require IP/common-law screening before promotion. Дата: 2026-09-23 09:36:38.256823+00.
- **giftability**: 7.50 (confidence 0.580). Initial Forge concept score using current occupational terminology, sampled marketplace patterns and technical distinctiveness. No visual has been generated; exact phrases still require IP/common-law screening before promotion. Дата: 2026-09-23 09:36:38.256823+00.
- **insider_resonance**: 10.00 (confidence 0.820). Initial Forge concept score using current occupational terminology, sampled marketplace patterns and technical distinctiveness. No visual has been generated; exact phrases still require IP/common-law screening before promotion. Дата: 2026-09-23 09:36:38.256823+00.
- **ip_safety**: 9.00 (confidence 0.660). Initial Forge concept score using current occupational terminology, sampled marketplace patterns and technical distinctiveness. No visual has been generated; exact phrases still require IP/common-law screening before promotion. Дата: 2026-09-23 09:36:38.256823+00.
- **niche_fit**: 10.00 (confidence 0.820). Initial Forge concept score using current occupational terminology, sampled marketplace patterns and technical distinctiveness. No visual has been generated; exact phrases still require IP/common-law screening before promotion. Дата: 2026-09-23 09:36:38.256823+00.
- **visual_potential**: 10.00 (confidence 0.800). Initial Forge concept score using current occupational terminology, sampled marketplace patterns and technical distinctiveness. No visual has been generated; exact phrases still require IP/common-law screening before promotion. Дата: 2026-09-23 09:36:38.256823+00.

#### NDT — visual testing
`ndt_vt_surface_observe_record` · ID `8f061114-8714-4fe9-86f6-d09014ef9d42`

**Интерпретация:** Исследовательский кандидат; одобрение владельца не зафиксировано
**Статус БД:** scored · **балл:** 84.90 · **confidence:** 67.17 · **coverage:** 100.00
**Текст / хук:** OBSERVE • EVALUATE • RECORD
**Идея:** NDT — visual testing. Core hook: OBSERVE • EVALUATE • RECORD. Inspection-method identity, indication evaluation and technical interpretation. Execution must stay original and descriptive; avoid employer, OEM, certification-body, association and proprietary-interface branding.
**Покупатель:** NDT/NDE technicians and inspectors
**Причина покупки:** Identity purchase for ndt/nde technicians and inspectors who recognize the real workflow/systems language.
**Отличие:** Insider technical workflow direction intended to avoid generic profession-title, retro-badge, skull, flag, coffee and parody templates.
**Визуальное направление:** Visual-testing concept centered on inspection judgment and documentation, not generic welding art.
**Создано / обновлено:** 2026-09-23 09:48:50.541446+00 / 2026-09-23 09:55:40.114238+00

Компоненты оценки:
- **buyer_desire**: 8.11 (confidence 0.660). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **clarity_at_glance**: 9.13 (confidence 0.660). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **distinctiveness**: 8.30 (confidence 0.660). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **giftability**: 8.03 (confidence 0.660). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **insider_resonance**: 8.75 (confidence 0.690). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **ip_safety**: 9.00 (confidence 0.660). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **niche_fit**: 9.21 (confidence 0.690). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **visual_potential**: 8.35 (confidence 0.690). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.

## 31. Nuclear Medicine Technologist
Ключ: `nuclear_medicine_technologist` · ID: `dc542fff-fd7a-4fec-a4ee-95972b5d0dc8`

**Статус БД:** scored · **балл:** 77.55 · **confidence:** 71.62 · **coverage:** 100.00
**Аудитория:** Nuclear medicine technologists in hospitals, imaging centers and clinics
**Категория:** occupational_identity
**Исследовательская аргументация:** Compact imaging specialty with strong identity around radiopharmaceuticals, activity, uptake, PET/SPECT and radiation safety. Current sampled marketplace shows dedicated items but not the broad saturation seen in sonography/MLS.
**Создано / обновлено:** 2026-09-23 09:42:54.27545+00 / 2026-09-23 09:43:36.792084+00

### Компоненты оценки ниши

- **channel_breadth**: 7.00 (confidence 0.580). Forge hidden-trades v2 initial score using current BLS/O*NET occupational evidence plus sampled Etsy marketplace depth. Scores prioritize buyer identity and whitespace, not raw occupation size. Benchmark niches intentionally receive competition penalties. Дата: 2026-09-23 09:43:36.792084+00.
- **competition_opportunity**: 7.00 (confidence 0.580). Forge hidden-trades v2 initial score using current BLS/O*NET occupational evidence plus sampled Etsy marketplace depth. Scores prioritize buyer identity and whitespace, not raw occupation size. Benchmark niches intentionally receive competition penalties. Дата: 2026-09-23 09:43:36.792084+00.
- **concept_depth**: 9.50 (confidence 0.780). Forge hidden-trades v2 initial score using current BLS/O*NET occupational evidence plus sampled Etsy marketplace depth. Scores prioritize buyer identity and whitespace, not raw occupation size. Benchmark niches intentionally receive competition penalties. Дата: 2026-09-23 09:43:36.792084+00.
- **demand_evidence**: 6.50 (confidence 0.860). Forge hidden-trades v2 initial score using current BLS/O*NET occupational evidence plus sampled Etsy marketplace depth. Scores prioritize buyer identity and whitespace, not raw occupation size. Benchmark niches intentionally receive competition penalties. Дата: 2026-09-23 09:43:36.792084+00.
- **founder_edge**: 2.00 (confidence 0.400). Forge hidden-trades v2 initial score using current BLS/O*NET occupational evidence plus sampled Etsy marketplace depth. Scores prioritize buyer identity and whitespace, not raw occupation size. Benchmark niches intentionally receive competition penalties. Дата: 2026-09-23 09:43:36.792084+00.
- **identity_intensity**: 8.50 (confidence 0.720). Forge hidden-trades v2 initial score using current BLS/O*NET occupational evidence plus sampled Etsy marketplace depth. Scores prioritize buyer identity and whitespace, not raw occupation size. Benchmark niches intentionally receive competition penalties. Дата: 2026-09-23 09:43:36.792084+00.
- **legal_safety**: 8.00 (confidence 0.600). Forge hidden-trades v2 initial score using current BLS/O*NET occupational evidence plus sampled Etsy marketplace depth. Scores prioritize buyer identity and whitespace, not raw occupation size. Benchmark niches intentionally receive competition penalties. Дата: 2026-09-23 09:43:36.792084+00.
- **purchase_motivation**: 8.00 (confidence 0.680). Forge hidden-trades v2 initial score using current BLS/O*NET occupational evidence plus sampled Etsy marketplace depth. Scores prioritize buyer identity and whitespace, not raw occupation size. Benchmark niches intentionally receive competition penalties. Дата: 2026-09-23 09:43:36.792084+00.
- **repeatability**: 8.00 (confidence 0.660). Forge hidden-trades v2 initial score using current BLS/O*NET occupational evidence plus sampled Etsy marketplace depth. Scores prioritize buyer identity and whitespace, not raw occupation size. Benchmark niches intentionally receive competition penalties. Дата: 2026-09-23 09:43:36.792084+00.
- **visual_language**: 9.50 (confidence 0.820). Forge hidden-trades v2 initial score using current BLS/O*NET occupational evidence plus sampled Etsy marketplace depth. Scores prioritize buyer identity and whitespace, not raw occupation size. Benchmark niches intentionally receive competition penalties. Дата: 2026-09-23 09:43:36.792084+00.

### Концепции (0)

## 32. Occupational Health & Safety Technician
Ключ: `occupational_safety_technician` · ID: `6c6d60c8-4318-483d-8f23-1956b79c483d`

**Статус БД:** scored · **балл:** 74.45 · **confidence:** 72.94 · **coverage:** 100.00
**Аудитория:** EHS / workplace safety technicians
**Категория:** occupational_identity
**Исследовательская аргументация:** Legacy Town Label occupational niche carried forward for re-evaluation under the new niche-first scoring engine. Existing artwork quality does not determine niche status.
**Создано / обновлено:** 2026-09-23 06:11:01.997287+00 / 2026-09-23 09:44:55.053118+00

### Компоненты оценки ниши

- **channel_breadth**: 8.00 (confidence 0.640). Legacy Forge/Town Label niche rescored under the unified Forge rubric using current 2025-35 BLS data plus the 2026-09-21/22 marketplace and IP research already stored in merch.research_notes. Existing visual rejection does not count as niche rejection. Дата: 2026-09-23 09:44:55.053118+00.
- **competition_opportunity**: 4.00 (confidence 0.760). Legacy Forge/Town Label niche rescored under the unified Forge rubric using current 2025-35 BLS data plus the 2026-09-21/22 marketplace and IP research already stored in merch.research_notes. Existing visual rejection does not count as niche rejection. Дата: 2026-09-23 09:44:55.053118+00.
- **concept_depth**: 9.00 (confidence 0.740). Legacy Forge/Town Label niche rescored under the unified Forge rubric using current 2025-35 BLS data plus the 2026-09-21/22 marketplace and IP research already stored in merch.research_notes. Existing visual rejection does not count as niche rejection. Дата: 2026-09-23 09:44:55.053118+00.
- **demand_evidence**: 9.00 (confidence 0.900). Legacy Forge/Town Label niche rescored under the unified Forge rubric using current 2025-35 BLS data plus the 2026-09-21/22 marketplace and IP research already stored in merch.research_notes. Existing visual rejection does not count as niche rejection. Дата: 2026-09-23 09:44:55.053118+00.
- **founder_edge**: 2.00 (confidence 0.400). Legacy Forge/Town Label niche rescored under the unified Forge rubric using current 2025-35 BLS data plus the 2026-09-21/22 marketplace and IP research already stored in merch.research_notes. Existing visual rejection does not count as niche rejection. Дата: 2026-09-23 09:44:55.053118+00.
- **identity_intensity**: 7.50 (confidence 0.660). Legacy Forge/Town Label niche rescored under the unified Forge rubric using current 2025-35 BLS data plus the 2026-09-21/22 marketplace and IP research already stored in merch.research_notes. Existing visual rejection does not count as niche rejection. Дата: 2026-09-23 09:44:55.053118+00.
- **legal_safety**: 6.50 (confidence 0.700). Legacy Forge/Town Label niche rescored under the unified Forge rubric using current 2025-35 BLS data plus the 2026-09-21/22 marketplace and IP research already stored in merch.research_notes. Existing visual rejection does not count as niche rejection. Дата: 2026-09-23 09:44:55.053118+00.
- **purchase_motivation**: 7.50 (confidence 0.640). Legacy Forge/Town Label niche rescored under the unified Forge rubric using current 2025-35 BLS data plus the 2026-09-21/22 marketplace and IP research already stored in merch.research_notes. Existing visual rejection does not count as niche rejection. Дата: 2026-09-23 09:44:55.053118+00.
- **repeatability**: 8.00 (confidence 0.660). Legacy Forge/Town Label niche rescored under the unified Forge rubric using current 2025-35 BLS data plus the 2026-09-21/22 marketplace and IP research already stored in merch.research_notes. Existing visual rejection does not count as niche rejection. Дата: 2026-09-23 09:44:55.053118+00.
- **visual_language**: 8.50 (confidence 0.720). Legacy Forge/Town Label niche rescored under the unified Forge rubric using current 2025-35 BLS data plus the 2026-09-21/22 marketplace and IP research already stored in merch.research_notes. Existing visual rejection does not count as niche rejection. Дата: 2026-09-23 09:44:55.053118+00.

### Концепции (1)

#### Safety — inspect / test / evaluate
`safety_inspect_test_evaluate` · ID `2d575e2f-d779-406f-864a-32e1199c79dc`

**Интерпретация:** Исследовательский кандидат; одобрение владельца не зафиксировано
**Статус БД:** scored · **балл:** 85.94 · **confidence:** 71.80 · **coverage:** 100.00
**Текст / хук:** INSPECT • TEST • EVALUATE | HAZARD • CONTROL • REPORT
**Идея:** Occupational Health & Safety Technician professional workplace-safety identity graphic using INSPECT / TEST / EVALUATE and HAZARD / CONTROL / REPORT with an original checklist/risk-control schematic. Avoid certification logos, OSHA seals, employer logos, or implied official affiliation.
**Покупатель:** EHS / workplace safety technicians
**Создано / обновлено:** 2026-09-23 06:11:42.741293+00 / 2026-09-23 09:57:07.855981+00

Компоненты оценки:
- **buyer_desire**: 8.22 (confidence 0.730). Unified Forge concept-depth score. Profile captures the concept form (technical map, diagnostic, system map, workflow, process or terminology); a small stored concept bias and bounded niche-quality adjustment prevent identical form scores across materially different niches. No visual was generated. Federal/common-law phrase review remains a separate gate. Дата: 2026-09-23 09:51:32.257179+00.
- **clarity_at_glance**: 9.30 (confidence 0.760). Unified Forge concept-depth score. Profile captures the concept form (technical map, diagnostic, system map, workflow, process or terminology); a small stored concept bias and bounded niche-quality adjustment prevent identical form scores across materially different niches. No visual was generated. Federal/common-law phrase review remains a separate gate. Дата: 2026-09-23 09:51:32.257179+00.
- **distinctiveness**: 8.60 (confidence 0.715). Unified Forge concept-depth score. Profile captures the concept form (technical map, diagnostic, system map, workflow, process or terminology); a small stored concept bias and bounded niche-quality adjustment prevent identical form scores across materially different niches. No visual was generated. Federal/common-law phrase review remains a separate gate. Дата: 2026-09-23 09:51:32.257179+00.
- **giftability**: 8.02 (confidence 0.707). Unified Forge concept-depth score. Profile captures the concept form (technical map, diagnostic, system map, workflow, process or terminology); a small stored concept bias and bounded niche-quality adjustment prevent identical form scores across materially different niches. No visual was generated. Federal/common-law phrase review remains a separate gate. Дата: 2026-09-23 09:51:32.257179+00.
- **insider_resonance**: 8.90 (confidence 0.737). Unified Forge concept-depth score. Profile captures the concept form (technical map, diagnostic, system map, workflow, process or terminology); a small stored concept bias and bounded niche-quality adjustment prevent identical form scores across materially different niches. No visual was generated. Federal/common-law phrase review remains a separate gate. Дата: 2026-09-23 09:51:32.257179+00.
- **ip_safety**: 9.00 (confidence 0.550). Unified Forge concept-depth score. Profile captures the concept form (technical map, diagnostic, system map, workflow, process or terminology); a small stored concept bias and bounded niche-quality adjustment prevent identical form scores across materially different niches. No visual was generated. Federal/common-law phrase review remains a separate gate. Дата: 2026-09-23 09:51:32.257179+00.
- **niche_fit**: 8.92 (confidence 0.745). Unified Forge concept-depth score. Profile captures the concept form (technical map, diagnostic, system map, workflow, process or terminology); a small stored concept bias and bounded niche-quality adjustment prevent identical form scores across materially different niches. No visual was generated. Federal/common-law phrase review remains a separate gate. Дата: 2026-09-23 09:51:32.257179+00.
- **visual_potential**: 8.40 (confidence 0.707). Unified Forge concept-depth score. Profile captures the concept form (technical map, diagnostic, system map, workflow, process or terminology); a small stored concept bias and bounded niche-quality adjustment prevent identical form scores across materially different niches. No visual was generated. Federal/common-law phrase review remains a separate gate. Дата: 2026-09-23 09:51:32.257179+00.

## 33. Ophthalmic Medical Technician
Ключ: `ophthalmic_medical_technician` · ID: `58d43e55-4ac2-4768-b567-98197b18b37d`

**Статус БД:** shortlisted · **балл:** 84.95 · **confidence:** 68.98 · **coverage:** 100.00
**Аудитория:** Ophthalmic medical technicians working with ophthalmologists
**Категория:** occupational_identity
**Исследовательская аргументация:** Fast-growing eye-care technician occupation with instrument-heavy clinical visual language. Sampled exact Etsy search did not surface a strong dedicated category, making it worth deeper validation.
**Создано / обновлено:** 2026-09-23 09:56:40.513406+00 / 2026-09-23 10:03:30.159451+00

### Компоненты оценки ниши

- **channel_breadth**: 8.00 (confidence 0.620). Forge diversity-batch v3 score using current 2025-35 BLS/O*NET evidence plus sampled current Etsy competition. Where exact marketplace counts were unavailable, competition confidence is intentionally lower. Дата: 2026-09-23 09:56:40.513406+00.
- **competition_opportunity**: 8.50 (confidence 0.460). Forge diversity-batch v3 score using current 2025-35 BLS/O*NET evidence plus sampled current Etsy competition. Where exact marketplace counts were unavailable, competition confidence is intentionally lower. Дата: 2026-09-23 09:56:40.513406+00.
- **concept_depth**: 9.00 (confidence 0.740). Forge diversity-batch v3 score using current 2025-35 BLS/O*NET evidence plus sampled current Etsy competition. Where exact marketplace counts were unavailable, competition confidence is intentionally lower. Дата: 2026-09-23 09:56:40.513406+00.
- **demand_evidence**: 9.50 (confidence 0.940). Forge diversity-batch v3 score using current 2025-35 BLS/O*NET evidence plus sampled current Etsy competition. Where exact marketplace counts were unavailable, competition confidence is intentionally lower. Дата: 2026-09-23 09:56:40.513406+00.
- **founder_edge**: 2.00 (confidence 0.400). Forge diversity-batch v3 score using current 2025-35 BLS/O*NET evidence plus sampled current Etsy competition. Where exact marketplace counts were unavailable, competition confidence is intentionally lower. Дата: 2026-09-23 09:56:40.513406+00.
- **identity_intensity**: 8.00 (confidence 0.660). Forge diversity-batch v3 score using current 2025-35 BLS/O*NET evidence plus sampled current Etsy competition. Where exact marketplace counts were unavailable, competition confidence is intentionally lower. Дата: 2026-09-23 09:56:40.513406+00.
- **legal_safety**: 8.00 (confidence 0.600). Forge diversity-batch v3 score using current 2025-35 BLS/O*NET evidence plus sampled current Etsy competition. Where exact marketplace counts were unavailable, competition confidence is intentionally lower. Дата: 2026-09-23 09:56:40.513406+00.
- **purchase_motivation**: 8.00 (confidence 0.620). Forge diversity-batch v3 score using current 2025-35 BLS/O*NET evidence plus sampled current Etsy competition. Where exact marketplace counts were unavailable, competition confidence is intentionally lower. Дата: 2026-09-23 09:56:40.513406+00.
- **repeatability**: 8.00 (confidence 0.620). Forge diversity-batch v3 score using current 2025-35 BLS/O*NET evidence plus sampled current Etsy competition. Where exact marketplace counts were unavailable, competition confidence is intentionally lower. Дата: 2026-09-23 09:56:40.513406+00.
- **visual_language**: 9.50 (confidence 0.800). Forge diversity-batch v3 score using current 2025-35 BLS/O*NET evidence plus sampled current Etsy competition. Where exact marketplace counts were unavailable, competition confidence is intentionally lower. Дата: 2026-09-23 09:56:40.513406+00.

### Концепции (17)

#### Ophthalmic — equipment stack
`oph_autorefractor_phoropter_tomograph_tonometer` · ID `6da5604b-bef4-4587-8936-7a2867d61341`

**Интерпретация:** Исследовательский кандидат; одобрение владельца не зафиксировано
**Статус БД:** scored · **балл:** 87.91 · **confidence:** 67.17 · **coverage:** 100.00
**Текст / хук:** AUTOREFRACTOR • PHOROPTER • TOMOGRAPH • TONOMETER
**Идея:** Ophthalmic — equipment stack. Core hook: AUTOREFRACTOR • PHOROPTER • TOMOGRAPH • TONOMETER. Grounded in current occupational tasks and intended as insider identity art, not operating/medical instruction. Avoid employer, OEM, certification-body and proprietary-interface branding.
**Покупатель:** Ophthalmic medical technicians
**Причина покупки:** Professional identity purchase for ophthalmic medical technicians who recognize the real tools, measurements and workflow.
**Отличие:** Technical terminology direction designed to avoid generic job-title, floral, retro-badge and parody templates.
**Визуальное направление:** Equipment-family identity using generic silhouettes and optics lines, avoiding proprietary product shapes.
**Создано / обновлено:** 2026-09-23 10:02:18.463532+00 / 2026-09-23 10:02:33.245254+00

Компоненты оценки:
- **buyer_desire**: 8.27 (confidence 0.660). Provisional Forge challenger-concept score derived from occupationally grounded concept archetype plus the fully scored niche prior. It is a research-priority score, not a sales forecast or legal clearance. Дата: 2026-09-23 10:02:33.245254+00.
- **clarity_at_glance**: 9.30 (confidence 0.660). Provisional Forge challenger-concept score derived from occupationally grounded concept archetype plus the fully scored niche prior. It is a research-priority score, not a sales forecast or legal clearance. Дата: 2026-09-23 10:02:33.245254+00.
- **distinctiveness**: 8.60 (confidence 0.660). Provisional Forge challenger-concept score derived from occupationally grounded concept archetype plus the fully scored niche prior. It is a research-priority score, not a sales forecast or legal clearance. Дата: 2026-09-23 10:02:33.245254+00.
- **giftability**: 8.20 (confidence 0.660). Provisional Forge challenger-concept score derived from occupationally grounded concept archetype plus the fully scored niche prior. It is a research-priority score, not a sales forecast or legal clearance. Дата: 2026-09-23 10:02:33.245254+00.
- **insider_resonance**: 9.55 (confidence 0.690). Provisional Forge challenger-concept score derived from occupationally grounded concept archetype plus the fully scored niche prior. It is a research-priority score, not a sales forecast or legal clearance. Дата: 2026-09-23 10:02:33.245254+00.
- **ip_safety**: 8.80 (confidence 0.660). Provisional Forge challenger-concept score derived from occupationally grounded concept archetype plus the fully scored niche prior. It is a research-priority score, not a sales forecast or legal clearance. Дата: 2026-09-23 10:02:33.245254+00.
- **niche_fit**: 9.54 (confidence 0.690). Provisional Forge challenger-concept score derived from occupationally grounded concept archetype plus the fully scored niche prior. It is a research-priority score, not a sales forecast or legal clearance. Дата: 2026-09-23 10:02:33.245254+00.
- **visual_potential**: 8.55 (confidence 0.690). Provisional Forge challenger-concept score derived from occupationally grounded concept archetype plus the fully scored niche prior. It is a research-priority score, not a sales forecast or legal clearance. Дата: 2026-09-23 10:02:33.245254+00.

#### Ophthalmic — instrument to record
`oph_eye_instrument_measure_document` · ID `8bcf56d3-d5fe-4527-8f6f-f2e44bb0e740`

**Интерпретация:** Исследовательский кандидат; одобрение владельца не зафиксировано
**Статус БД:** scored · **балл:** 88.47 · **confidence:** 69.17 · **coverage:** 100.00
**Текст / хук:** EYE → INSTRUMENT → MEASURE → DOCUMENT
**Идея:** Ophthalmic — instrument to record. Core hook: EYE → INSTRUMENT → MEASURE → DOCUMENT. Grounded in current occupational tasks and intended as insider identity art, not operating/medical instruction. Avoid employer, OEM, certification-body and proprietary-interface branding.
**Покупатель:** Ophthalmic medical technicians
**Причина покупки:** Professional identity purchase for ophthalmic medical technicians who recognize the real tools, measurements and workflow.
**Отличие:** Technical system map direction designed to avoid generic job-title, floral, retro-badge and parody templates.
**Визуальное направление:** Generic diagnostic chain from eye to instrument to recorded measurement.
**Создано / обновлено:** 2026-09-23 10:02:18.463532+00 / 2026-09-23 10:04:16.501026+00

Компоненты оценки:
- **buyer_desire**: 8.57 (confidence 0.680). Provisional Forge challenger-concept score derived from occupationally grounded concept archetype plus the fully scored niche prior. It is a research-priority score, not a sales forecast or legal clearance. Дата: 2026-09-23 10:02:33.245254+00.
- **clarity_at_glance**: 8.17 (confidence 0.680). Provisional Forge challenger-concept score derived from occupationally grounded concept archetype plus the fully scored niche prior. It is a research-priority score, not a sales forecast or legal clearance. Дата: 2026-09-23 10:02:33.245254+00.
- **distinctiveness**: 9.00 (confidence 0.680). Provisional Forge challenger-concept score derived from occupationally grounded concept archetype plus the fully scored niche prior. It is a research-priority score, not a sales forecast or legal clearance. Дата: 2026-09-23 10:02:33.245254+00.
- **giftability**: 7.57 (confidence 0.680). Provisional Forge challenger-concept score derived from occupationally grounded concept archetype plus the fully scored niche prior. It is a research-priority score, not a sales forecast or legal clearance. Дата: 2026-09-23 10:02:33.245254+00.
- **insider_resonance**: 9.10 (confidence 0.710). Provisional Forge challenger-concept score derived from occupationally grounded concept archetype plus the fully scored niche prior. It is a research-priority score, not a sales forecast or legal clearance. Дата: 2026-09-23 10:02:33.245254+00.
- **ip_safety**: 8.80 (confidence 0.680). Provisional Forge challenger-concept score derived from occupationally grounded concept archetype plus the fully scored niche prior. It is a research-priority score, not a sales forecast or legal clearance. Дата: 2026-09-23 10:02:33.245254+00.
- **niche_fit**: 9.44 (confidence 0.710). Provisional Forge challenger-concept score derived from occupationally grounded concept archetype plus the fully scored niche prior. It is a research-priority score, not a sales forecast or legal clearance. Дата: 2026-09-23 10:02:33.245254+00.
- **visual_potential**: 9.60 (confidence 0.710). Provisional Forge challenger-concept score derived from occupationally grounded concept archetype plus the fully scored niche prior. It is a research-priority score, not a sales forecast or legal clearance. Дата: 2026-09-23 10:02:33.245254+00.

#### Ophthalmic — clinical measurement flow
`oph_history_acuity_pressure_field` · ID `6be096f4-ee0f-430a-a3b1-ba8054657d5e`

**Интерпретация:** Исследовательский кандидат; одобрение владельца не зафиксировано
**Статус БД:** scored · **балл:** 85.96 · **confidence:** 67.17 · **coverage:** 100.00
**Текст / хук:** HISTORY → ACUITY → PRESSURE → FIELD
**Идея:** Ophthalmic — clinical measurement flow. Core hook: HISTORY → ACUITY → PRESSURE → FIELD. Grounded in current occupational tasks and intended as insider identity art, not operating/medical instruction. Avoid employer, OEM, certification-body and proprietary-interface branding.
**Покупатель:** Ophthalmic medical technicians
**Причина покупки:** Professional identity purchase for ophthalmic medical technicians who recognize the real tools, measurements and workflow.
**Отличие:** Technical workflow direction designed to avoid generic job-title, floral, retro-badge and parody templates.
**Визуальное направление:** High-level clinical workflow with measurement/documentation cues; identity art, not medical instruction.
**Создано / обновлено:** 2026-09-23 10:02:18.463532+00 / 2026-09-23 10:02:33.245254+00

Компоненты оценки:
- **buyer_desire**: 8.37 (confidence 0.660). Provisional Forge challenger-concept score derived from occupationally grounded concept archetype plus the fully scored niche prior. It is a research-priority score, not a sales forecast or legal clearance. Дата: 2026-09-23 10:02:33.245254+00.
- **clarity_at_glance**: 9.17 (confidence 0.660). Provisional Forge challenger-concept score derived from occupationally grounded concept archetype plus the fully scored niche prior. It is a research-priority score, not a sales forecast or legal clearance. Дата: 2026-09-23 10:02:33.245254+00.
- **distinctiveness**: 8.40 (confidence 0.660). Provisional Forge challenger-concept score derived from occupationally grounded concept archetype plus the fully scored niche prior. It is a research-priority score, not a sales forecast or legal clearance. Дата: 2026-09-23 10:02:33.245254+00.
- **giftability**: 8.07 (confidence 0.660). Provisional Forge challenger-concept score derived from occupationally grounded concept archetype plus the fully scored niche prior. It is a research-priority score, not a sales forecast or legal clearance. Дата: 2026-09-23 10:02:33.245254+00.
- **insider_resonance**: 8.80 (confidence 0.690). Provisional Forge challenger-concept score derived from occupationally grounded concept archetype plus the fully scored niche prior. It is a research-priority score, not a sales forecast or legal clearance. Дата: 2026-09-23 10:02:33.245254+00.
- **ip_safety**: 9.00 (confidence 0.660). Provisional Forge challenger-concept score derived from occupationally grounded concept archetype plus the fully scored niche prior. It is a research-priority score, not a sales forecast or legal clearance. Дата: 2026-09-23 10:02:33.245254+00.
- **niche_fit**: 9.34 (confidence 0.690). Provisional Forge challenger-concept score derived from occupationally grounded concept archetype plus the fully scored niche prior. It is a research-priority score, not a sales forecast or legal clearance. Дата: 2026-09-23 10:02:33.245254+00.
- **visual_potential**: 8.40 (confidence 0.690). Provisional Forge challenger-concept score derived from occupationally grounded concept archetype plus the fully scored niche prior. It is a research-priority score, not a sales forecast or legal clearance. Дата: 2026-09-23 10:02:33.245254+00.

#### Ophthalmic — core diagnostics
`oph_iop_field_acuity_refraction` · ID `9fc3bb1a-78f1-4a0c-8af8-f40d4f2adb10`

**Интерпретация:** Исторический: семантический дубликат
**Статус БД:** paused · **балл:** 87.91 · **confidence:** 67.17 · **coverage:** 100.00
**Текст / хук:** IOP • FIELD • ACUITY • REFRACTION
**Идея:** Ophthalmic — core diagnostics. Core hook: IOP • FIELD • ACUITY • REFRACTION. Grounded in current occupational tasks and intended as insider identity art, not operating/medical instruction. Avoid employer, OEM, certification-body and proprietary-interface branding.
**Покупатель:** Ophthalmic medical technicians
**Причина покупки:** Professional identity purchase for ophthalmic medical technicians who recognize the real tools, measurements and workflow.
**Отличие:** Technical terminology direction designed to avoid generic job-title, floral, retro-badge and parody templates.
**Визуальное направление:** Four-domain eye-testing identity with original eye/instrument geometry; no clinic branding or procedural values.
**semantic_duplicate_of:** ophth_acuity_pressure_refraction
**semantic_duplicate_reason:** Same core ophthalmic diagnostic-domain list; IOP is pressure and FIELD is incremental, not a materially new buyer hook.
**Создано / обновлено:** 2026-09-23 10:02:18.463532+00 / 2026-09-23 10:05:50.016716+00

Компоненты оценки:
- **buyer_desire**: 8.27 (confidence 0.660). Provisional Forge challenger-concept score derived from occupationally grounded concept archetype plus the fully scored niche prior. It is a research-priority score, not a sales forecast or legal clearance. Дата: 2026-09-23 10:02:33.245254+00.
- **clarity_at_glance**: 9.30 (confidence 0.660). Provisional Forge challenger-concept score derived from occupationally grounded concept archetype plus the fully scored niche prior. It is a research-priority score, not a sales forecast or legal clearance. Дата: 2026-09-23 10:02:33.245254+00.
- **distinctiveness**: 8.60 (confidence 0.660). Provisional Forge challenger-concept score derived from occupationally grounded concept archetype plus the fully scored niche prior. It is a research-priority score, not a sales forecast or legal clearance. Дата: 2026-09-23 10:02:33.245254+00.
- **giftability**: 8.20 (confidence 0.660). Provisional Forge challenger-concept score derived from occupationally grounded concept archetype plus the fully scored niche prior. It is a research-priority score, not a sales forecast or legal clearance. Дата: 2026-09-23 10:02:33.245254+00.
- **insider_resonance**: 9.55 (confidence 0.690). Provisional Forge challenger-concept score derived from occupationally grounded concept archetype plus the fully scored niche prior. It is a research-priority score, not a sales forecast or legal clearance. Дата: 2026-09-23 10:02:33.245254+00.
- **ip_safety**: 8.80 (confidence 0.660). Provisional Forge challenger-concept score derived from occupationally grounded concept archetype plus the fully scored niche prior. It is a research-priority score, not a sales forecast or legal clearance. Дата: 2026-09-23 10:02:33.245254+00.
- **niche_fit**: 9.54 (confidence 0.690). Provisional Forge challenger-concept score derived from occupationally grounded concept archetype plus the fully scored niche prior. It is a research-priority score, not a sales forecast or legal clearance. Дата: 2026-09-23 10:02:33.245254+00.
- **visual_potential**: 8.55 (confidence 0.690). Provisional Forge challenger-concept score derived from occupationally grounded concept archetype plus the fully scored niche prior. It is a research-priority score, not a sales forecast or legal clearance. Дата: 2026-09-23 10:02:33.245254+00.

#### Ophthalmic — measure / record / assist
`oph_measure_record_verify_assist` · ID `32923918-413c-470b-a66e-36161622f9fd`

**Интерпретация:** Исторический: семантический дубликат
**Статус БД:** paused · **балл:** 85.34 · **confidence:** 67.17 · **coverage:** 100.00
**Текст / хук:** MEASURE • RECORD • VERIFY • ASSIST
**Идея:** Ophthalmic — measure / record / assist. Core hook: MEASURE • RECORD • VERIFY • ASSIST. Grounded in current occupational tasks and intended as insider identity art, not operating/medical instruction. Avoid employer, OEM, certification-body and proprietary-interface branding.
**Покупатель:** Ophthalmic medical technicians
**Причина покупки:** Professional identity purchase for ophthalmic medical technicians who recognize the real tools, measurements and workflow.
**Отличие:** Technical workflow direction designed to avoid generic job-title, floral, retro-badge and parody templates.
**Визуальное направление:** Compact professional workflow around diagnostic measurement and physician support.
**semantic_duplicate_of:** ophth_tonometry_measure_record
**semantic_duplicate_reason:** Generic measure/record workflow materially overlaps the stronger tonometry-specific measurement concept.
**Создано / обновлено:** 2026-09-23 10:02:18.463532+00 / 2026-09-23 10:05:50.016716+00

Компоненты оценки:
- **buyer_desire**: 8.27 (confidence 0.660). Provisional Forge challenger-concept score derived from occupationally grounded concept archetype plus the fully scored niche prior. It is a research-priority score, not a sales forecast or legal clearance. Дата: 2026-09-23 10:02:33.245254+00.
- **clarity_at_glance**: 9.13 (confidence 0.660). Provisional Forge challenger-concept score derived from occupationally grounded concept archetype plus the fully scored niche prior. It is a research-priority score, not a sales forecast or legal clearance. Дата: 2026-09-23 10:02:33.245254+00.
- **distinctiveness**: 8.30 (confidence 0.660). Provisional Forge challenger-concept score derived from occupationally grounded concept archetype plus the fully scored niche prior. It is a research-priority score, not a sales forecast or legal clearance. Дата: 2026-09-23 10:02:33.245254+00.
- **giftability**: 8.03 (confidence 0.660). Provisional Forge challenger-concept score derived from occupationally grounded concept archetype plus the fully scored niche prior. It is a research-priority score, not a sales forecast or legal clearance. Дата: 2026-09-23 10:02:33.245254+00.
- **insider_resonance**: 8.75 (confidence 0.690). Provisional Forge challenger-concept score derived from occupationally grounded concept archetype plus the fully scored niche prior. It is a research-priority score, not a sales forecast or legal clearance. Дата: 2026-09-23 10:02:33.245254+00.
- **ip_safety**: 9.00 (confidence 0.660). Provisional Forge challenger-concept score derived from occupationally grounded concept archetype plus the fully scored niche prior. It is a research-priority score, not a sales forecast or legal clearance. Дата: 2026-09-23 10:02:33.245254+00.
- **niche_fit**: 9.34 (confidence 0.690). Provisional Forge challenger-concept score derived from occupationally grounded concept archetype plus the fully scored niche prior. It is a research-priority score, not a sales forecast or legal clearance. Дата: 2026-09-23 10:02:33.245254+00.
- **visual_potential**: 8.35 (confidence 0.690). Provisional Forge challenger-concept score derived from occupationally grounded concept archetype plus the fully scored niche prior. It is a research-priority score, not a sales forecast or legal clearance. Дата: 2026-09-23 10:02:33.245254+00.

#### Ophthalmic — instrument matrix
`oph_tonometry_retinoscopy_keratometry_lensometry` · ID `6cf6728d-08e9-473b-8fc4-f2603533bbca`

**Интерпретация:** Исследовательский кандидат; одобрение владельца не зафиксировано
**Статус БД:** scored · **балл:** 89.08 · **confidence:** 68.17 · **coverage:** 100.00
**Текст / хук:** TONOMETRY • RETINOSCOPY • KERATOMETRY • LENSOMETRY
**Идея:** Ophthalmic — instrument matrix. Core hook: TONOMETRY • RETINOSCOPY • KERATOMETRY • LENSOMETRY. Grounded in current occupational tasks and intended as insider identity art, not operating/medical instruction. Avoid employer, OEM, certification-body and proprietary-interface branding.
**Покупатель:** Ophthalmic medical technicians
**Причина покупки:** Professional identity purchase for ophthalmic medical technicians who recognize the real tools, measurements and workflow.
**Отличие:** Technical technical map direction designed to avoid generic job-title, floral, retro-badge and parody templates.
**Визуальное направление:** Instrument/test matrix using original generic optical symbols; no manufacturer UI.
**Создано / обновлено:** 2026-09-23 10:02:18.463532+00 / 2026-09-23 10:04:16.501026+00

Компоненты оценки:
- **buyer_desire**: 8.57 (confidence 0.670). Provisional Forge challenger-concept score derived from occupationally grounded concept archetype plus the fully scored niche prior. It is a research-priority score, not a sales forecast or legal clearance. Дата: 2026-09-23 10:02:33.245254+00.
- **clarity_at_glance**: 7.80 (confidence 0.670). Provisional Forge challenger-concept score derived from occupationally grounded concept archetype plus the fully scored niche prior. It is a research-priority score, not a sales forecast or legal clearance. Дата: 2026-09-23 10:02:33.245254+00.
- **distinctiveness**: 9.30 (confidence 0.670). Provisional Forge challenger-concept score derived from occupationally grounded concept archetype plus the fully scored niche prior. It is a research-priority score, not a sales forecast or legal clearance. Дата: 2026-09-23 10:02:33.245254+00.
- **giftability**: 7.50 (confidence 0.670). Provisional Forge challenger-concept score derived from occupationally grounded concept archetype plus the fully scored niche prior. It is a research-priority score, not a sales forecast or legal clearance. Дата: 2026-09-23 10:02:33.245254+00.
- **insider_resonance**: 9.35 (confidence 0.700). Provisional Forge challenger-concept score derived from occupationally grounded concept archetype plus the fully scored niche prior. It is a research-priority score, not a sales forecast or legal clearance. Дата: 2026-09-23 10:02:33.245254+00.
- **ip_safety**: 8.60 (confidence 0.670). Provisional Forge challenger-concept score derived from occupationally grounded concept archetype plus the fully scored niche prior. It is a research-priority score, not a sales forecast or legal clearance. Дата: 2026-09-23 10:02:33.245254+00.
- **niche_fit**: 9.44 (confidence 0.700). Provisional Forge challenger-concept score derived from occupationally grounded concept archetype plus the fully scored niche prior. It is a research-priority score, not a sales forecast or legal clearance. Дата: 2026-09-23 10:02:33.245254+00.
- **visual_potential**: 9.65 (confidence 0.700). Provisional Forge challenger-concept score derived from occupationally grounded concept archetype plus the fully scored niche prior. It is a research-priority score, not a sales forecast or legal clearance. Дата: 2026-09-23 10:02:33.245254+00.

#### Ophthalmic — acuity / pressure / refraction
`ophth_acuity_pressure_refraction` · ID `7212e10e-14cc-4ce0-a46d-4f1a43d60043`

**Интерпретация:** Исследовательский кандидат; одобрение владельца не зафиксировано
**Статус БД:** scored · **балл:** 88.55 · **confidence:** 70.34 · **coverage:** 100.00
**Текст / хук:** ACUITY • PRESSURE • REFRACTION
**Идея:** ACUITY • PRESSURE • REFRACTION as three ophthalmic-tech domains supported by original measurement geometry.
**Покупатель:** Ophthalmic medical technicians and ophthalmic assistants
**Причина покупки:** Broad but still profession-specific technician identity.
**Отличие:** Three technical domains instead of generic healthcare slogans.
**Визуальное направление:** Three-domain measurement composition.
**Создано / обновлено:** 2026-09-23 09:59:11.838032+00 / 2026-09-23 10:05:50.016716+00

Компоненты оценки:
- **buyer_desire**: 8.90 (confidence 0.712). Unified Forge diversity-v3 concept score grounded in current occupational tasks and niche evidence. No visual generated; phrase/IP review remains separate. Дата: 2026-09-23 09:59:11.838032+00.
- **clarity_at_glance**: 9.30 (confidence 0.742). Unified Forge diversity-v3 concept score grounded in current occupational tasks and niche evidence. No visual generated; phrase/IP review remains separate. Дата: 2026-09-23 09:59:11.838032+00.
- **distinctiveness**: 8.40 (confidence 0.682). Unified Forge diversity-v3 concept score grounded in current occupational tasks and niche evidence. No visual generated; phrase/IP review remains separate. Дата: 2026-09-23 09:59:11.838032+00.
- **giftability**: 8.80 (confidence 0.705). Unified Forge diversity-v3 concept score grounded in current occupational tasks and niche evidence. No visual generated; phrase/IP review remains separate. Дата: 2026-09-23 09:59:11.838032+00.
- **insider_resonance**: 9.50 (confidence 0.757). Unified Forge diversity-v3 concept score grounded in current occupational tasks and niche evidence. No visual generated; phrase/IP review remains separate. Дата: 2026-09-23 09:59:11.838032+00.
- **ip_safety**: 8.00 (confidence 0.500). Unified Forge diversity-v3 concept score grounded in current occupational tasks and niche evidence. No visual generated; phrase/IP review remains separate. Дата: 2026-09-23 09:59:11.838032+00.
- **niche_fit**: 9.90 (confidence 0.765). Unified Forge diversity-v3 concept score grounded in current occupational tasks and niche evidence. No visual generated; phrase/IP review remains separate. Дата: 2026-09-23 09:59:11.838032+00.
- **visual_potential**: 8.10 (confidence 0.667). Unified Forge diversity-v3 concept score grounded in current occupational tasks and niche evidence. No visual generated; phrase/IP review remains separate. Дата: 2026-09-23 09:59:11.838032+00.

#### Ophthalmic — test / image / document
`ophth_exam_test_image_document` · ID `24d849f4-a1fc-4073-b2db-46b548dc38d1`

**Интерпретация:** Исследовательский кандидат; одобрение владельца не зафиксировано
**Статус БД:** scored · **балл:** 88.72 · **confidence:** 70.85 · **coverage:** 100.00
**Текст / хук:** TEST → IMAGE → DOCUMENT
**Идея:** TEST → IMAGE → DOCUMENT as a generic ophthalmic diagnostic workflow linking testing, imaging and documentation.
**Покупатель:** Ophthalmic medical technicians and ophthalmic assistants
**Причина покупки:** Clear technician workflow with good at-a-glance readability.
**Отличие:** Workflow identity rather than treatment advice or generic eye-care art.
**Визуальное направление:** Generic diagnostic workflow graphic.
**Создано / обновлено:** 2026-09-23 09:59:11.838032+00 / 2026-09-23 09:59:11.838032+00

Компоненты оценки:
- **buyer_desire**: 8.80 (confidence 0.720). Unified Forge diversity-v3 concept score grounded in current occupational tasks and niche evidence. No visual generated; phrase/IP review remains separate. Дата: 2026-09-23 09:59:11.838032+00.
- **clarity_at_glance**: 9.40 (confidence 0.750). Unified Forge diversity-v3 concept score grounded in current occupational tasks and niche evidence. No visual generated; phrase/IP review remains separate. Дата: 2026-09-23 09:59:11.838032+00.
- **distinctiveness**: 8.70 (confidence 0.705). Unified Forge diversity-v3 concept score grounded in current occupational tasks and niche evidence. No visual generated; phrase/IP review remains separate. Дата: 2026-09-23 09:59:11.838032+00.
- **giftability**: 8.60 (confidence 0.697). Unified Forge diversity-v3 concept score grounded in current occupational tasks and niche evidence. No visual generated; phrase/IP review remains separate. Дата: 2026-09-23 09:59:11.838032+00.
- **insider_resonance**: 9.00 (confidence 0.727). Unified Forge diversity-v3 concept score grounded in current occupational tasks and niche evidence. No visual generated; phrase/IP review remains separate. Дата: 2026-09-23 09:59:11.838032+00.
- **ip_safety**: 9.10 (confidence 0.550). Unified Forge diversity-v3 concept score grounded in current occupational tasks and niche evidence. No visual generated; phrase/IP review remains separate. Дата: 2026-09-23 09:59:11.838032+00.
- **niche_fit**: 9.50 (confidence 0.735). Unified Forge diversity-v3 concept score grounded in current occupational tasks and niche evidence. No visual generated; phrase/IP review remains separate. Дата: 2026-09-23 09:59:11.838032+00.
- **visual_potential**: 8.50 (confidence 0.697). Unified Forge diversity-v3 concept score grounded in current occupational tasks and niche evidence. No visual generated; phrase/IP review remains separate. Дата: 2026-09-23 09:59:11.838032+00.

#### Ophthalmic — sphere / cylinder / axis
`ophth_refraction_sphere_cylinder_axis` · ID `db3bc508-58bd-4bee-9f50-82aa05f74888`

**Интерпретация:** Исследовательский кандидат; одобрение владельца не зафиксировано
**Статус БД:** scored · **балл:** 88.55 · **confidence:** 70.34 · **coverage:** 100.00
**Текст / хук:** SPHERE • CYLINDER • AXIS
**Идея:** Ophthalmic technician identity around SPHERE • CYLINDER • AXIS using original optics/grid geometry without copying a phoropter brand, chart, or clinic asset.
**Покупатель:** Ophthalmic medical technicians and ophthalmic assistants
**Причина покупки:** Identity purchase built on familiar refraction vocabulary.
**Отличие:** Specific refraction language instead of generic glasses graphics.
**Визуальное направление:** Original optics/grid composition.
**Создано / обновлено:** 2026-09-23 09:59:11.838032+00 / 2026-09-23 09:59:11.838032+00

Компоненты оценки:
- **buyer_desire**: 8.90 (confidence 0.712). Unified Forge diversity-v3 concept score grounded in current occupational tasks and niche evidence. No visual generated; phrase/IP review remains separate. Дата: 2026-09-23 09:59:11.838032+00.
- **clarity_at_glance**: 9.30 (confidence 0.742). Unified Forge diversity-v3 concept score grounded in current occupational tasks and niche evidence. No visual generated; phrase/IP review remains separate. Дата: 2026-09-23 09:59:11.838032+00.
- **distinctiveness**: 8.40 (confidence 0.682). Unified Forge diversity-v3 concept score grounded in current occupational tasks and niche evidence. No visual generated; phrase/IP review remains separate. Дата: 2026-09-23 09:59:11.838032+00.
- **giftability**: 8.80 (confidence 0.705). Unified Forge diversity-v3 concept score grounded in current occupational tasks and niche evidence. No visual generated; phrase/IP review remains separate. Дата: 2026-09-23 09:59:11.838032+00.
- **insider_resonance**: 9.50 (confidence 0.757). Unified Forge diversity-v3 concept score grounded in current occupational tasks and niche evidence. No visual generated; phrase/IP review remains separate. Дата: 2026-09-23 09:59:11.838032+00.
- **ip_safety**: 8.00 (confidence 0.500). Unified Forge diversity-v3 concept score grounded in current occupational tasks and niche evidence. No visual generated; phrase/IP review remains separate. Дата: 2026-09-23 09:59:11.838032+00.
- **niche_fit**: 9.90 (confidence 0.765). Unified Forge diversity-v3 concept score grounded in current occupational tasks and niche evidence. No visual generated; phrase/IP review remains separate. Дата: 2026-09-23 09:59:11.838032+00.
- **visual_potential**: 8.10 (confidence 0.667). Unified Forge diversity-v3 concept score grounded in current occupational tasks and niche evidence. No visual generated; phrase/IP review remains separate. Дата: 2026-09-23 09:59:11.838032+00.

#### Ophthalmic — retinoscopy / refraction
`ophth_retinoscopy_refraction` · ID `4754a77e-a482-4902-8517-f96d4ee60365`

**Интерпретация:** Исследовательский кандидат; одобрение владельца не зафиксировано
**Статус БД:** scored · **балл:** 89.19 · **confidence:** 71.44 · **coverage:** 100.00
**Текст / хук:** LIGHT • REFLEX • REFRACTION
**Идея:** LIGHT • REFLEX • REFRACTION using an original optical-ray/reflex motif referencing retinoscopy and refraction without procedural values or branded equipment.
**Покупатель:** Ophthalmic medical technicians and ophthalmic assistants
**Причина покупки:** Insider optics language with a distinctive technical visual.
**Отличие:** Avoids generic ophthalmology icons and clinic branding.
**Визуальное направление:** Original optical-ray/reflex geometry.
**Создано / обновлено:** 2026-09-23 09:59:11.838032+00 / 2026-09-23 09:59:11.838032+00

Компоненты оценки:
- **buyer_desire**: 8.50 (confidence 0.712). Unified Forge diversity-v3 concept score grounded in current occupational tasks and niche evidence. No visual generated; phrase/IP review remains separate. Дата: 2026-09-23 09:59:11.838032+00.
- **clarity_at_glance**: 7.80 (confidence 0.682). Unified Forge diversity-v3 concept score grounded in current occupational tasks and niche evidence. No visual generated; phrase/IP review remains separate. Дата: 2026-09-23 09:59:11.838032+00.
- **distinctiveness**: 9.30 (confidence 0.727). Unified Forge diversity-v3 concept score grounded in current occupational tasks and niche evidence. No visual generated; phrase/IP review remains separate. Дата: 2026-09-23 09:59:11.838032+00.
- **giftability**: 7.50 (confidence 0.667). Unified Forge diversity-v3 concept score grounded in current occupational tasks and niche evidence. No visual generated; phrase/IP review remains separate. Дата: 2026-09-23 09:59:11.838032+00.
- **insider_resonance**: 9.30 (confidence 0.742). Unified Forge diversity-v3 concept score grounded in current occupational tasks and niche evidence. No visual generated; phrase/IP review remains separate. Дата: 2026-09-23 09:59:11.838032+00.
- **ip_safety**: 8.80 (confidence 0.550). Unified Forge diversity-v3 concept score grounded in current occupational tasks and niche evidence. No visual generated; phrase/IP review remains separate. Дата: 2026-09-23 09:59:11.838032+00.
- **niche_fit**: 9.70 (confidence 0.742). Unified Forge diversity-v3 concept score grounded in current occupational tasks and niche evidence. No visual generated; phrase/IP review remains separate. Дата: 2026-09-23 09:59:11.838032+00.
- **visual_potential**: 9.70 (confidence 0.757). Unified Forge diversity-v3 concept score grounded in current occupational tasks and niche evidence. No visual generated; phrase/IP review remains separate. Дата: 2026-09-23 09:59:11.838032+00.

#### Ophthalmic — tonometry / measure / record
`ophth_tonometry_measure_record` · ID `58d4843b-e345-4065-81eb-687272780819`

**Интерпретация:** Исторический: снят после owner review; не возвращать автоматически
**Статус БД:** scored · **балл:** 90.12 · **confidence:** 71.96 · **coverage:** 100.00
**Текст / хук:** PRESSURE • MEASURE • RECORD
**Идея:** Ophthalmic technician identity around PRESSURE • MEASURE • RECORD with an original generic tonometry/instrument readout motif; descriptive profession art, not clinical instruction.
**Покупатель:** Ophthalmic medical technicians and ophthalmic assistants
**Причина покупки:** Identity purchase for ophthalmic technicians who recognize the measurement workflow.
**Отличие:** Profession-specific technical language rather than generic eye-care or nurse merch.
**Визуальное направление:** Original tonometry/instrument readout motif; no branded device UI.
**retired_reason:** failed purchase-trigger quality bar after owner review
**Создано / обновлено:** 2026-09-23 09:59:11.838032+00 / 2026-09-23 23:40:31.847823+00

Компоненты оценки:
- **buyer_desire**: 8.80 (confidence 0.720). Unified Forge diversity-v3 concept score grounded in current occupational tasks and niche evidence. No visual generated; phrase/IP review remains separate. Дата: 2026-09-23 09:59:11.838032+00.
- **clarity_at_glance**: 8.40 (confidence 0.705). Unified Forge diversity-v3 concept score grounded in current occupational tasks and niche evidence. No visual generated; phrase/IP review remains separate. Дата: 2026-09-23 09:59:11.838032+00.
- **distinctiveness**: 9.20 (confidence 0.735). Unified Forge diversity-v3 concept score grounded in current occupational tasks and niche evidence. No visual generated; phrase/IP review remains separate. Дата: 2026-09-23 09:59:11.838032+00.
- **giftability**: 8.00 (confidence 0.675). Unified Forge diversity-v3 concept score grounded in current occupational tasks and niche evidence. No visual generated; phrase/IP review remains separate. Дата: 2026-09-23 09:59:11.838032+00.
- **insider_resonance**: 9.50 (confidence 0.757). Unified Forge diversity-v3 concept score grounded in current occupational tasks and niche evidence. No visual generated; phrase/IP review remains separate. Дата: 2026-09-23 09:59:11.838032+00.
- **ip_safety**: 8.90 (confidence 0.550). Unified Forge diversity-v3 concept score grounded in current occupational tasks and niche evidence. No visual generated; phrase/IP review remains separate. Дата: 2026-09-23 09:59:11.838032+00.
- **niche_fit**: 9.90 (confidence 0.757). Unified Forge diversity-v3 concept score grounded in current occupational tasks and niche evidence. No visual generated; phrase/IP review remains separate. Дата: 2026-09-23 09:59:11.838032+00.
- **visual_potential**: 9.00 (confidence 0.727). Unified Forge diversity-v3 concept score grounded in current occupational tasks and niche evidence. No visual generated; phrase/IP review remains separate. Дата: 2026-09-23 09:59:11.838032+00.

#### Ophthalmic — visual field map
`ophth_visual_field_map` · ID `f46b0365-9b54-4e2f-a52f-01a633453307`

**Интерпретация:** Исторический: снят после owner review; не возвращать автоматически
**Статус БД:** scored · **балл:** 89.19 · **confidence:** 71.44 · **coverage:** 100.00
**Текст / хук:** FIELD • MAP • REVIEW
**Идея:** FIELD • MAP • REVIEW with an abstract visual-field point map and review grid; generic diagnostic identity, not a real patient result or device UI.
**Покупатель:** Ophthalmic medical technicians and ophthalmic assistants
**Причина покупки:** Technical diagnostic identity with strong visual potential.
**Отличие:** Visual-field mapping is more insider-specific than generic eye graphics.
**Визуальное направление:** Abstract visual-field point map and grid.
**retired_reason:** failed purchase-trigger quality bar after owner review
**Создано / обновлено:** 2026-09-23 09:59:11.838032+00 / 2026-09-23 23:40:31.847823+00

Компоненты оценки:
- **buyer_desire**: 8.50 (confidence 0.712). Unified Forge diversity-v3 concept score grounded in current occupational tasks and niche evidence. No visual generated; phrase/IP review remains separate. Дата: 2026-09-23 09:59:11.838032+00.
- **clarity_at_glance**: 7.80 (confidence 0.682). Unified Forge diversity-v3 concept score grounded in current occupational tasks and niche evidence. No visual generated; phrase/IP review remains separate. Дата: 2026-09-23 09:59:11.838032+00.
- **distinctiveness**: 9.30 (confidence 0.727). Unified Forge diversity-v3 concept score grounded in current occupational tasks and niche evidence. No visual generated; phrase/IP review remains separate. Дата: 2026-09-23 09:59:11.838032+00.
- **giftability**: 7.50 (confidence 0.667). Unified Forge diversity-v3 concept score grounded in current occupational tasks and niche evidence. No visual generated; phrase/IP review remains separate. Дата: 2026-09-23 09:59:11.838032+00.
- **insider_resonance**: 9.30 (confidence 0.742). Unified Forge diversity-v3 concept score grounded in current occupational tasks and niche evidence. No visual generated; phrase/IP review remains separate. Дата: 2026-09-23 09:59:11.838032+00.
- **ip_safety**: 8.80 (confidence 0.550). Unified Forge diversity-v3 concept score grounded in current occupational tasks and niche evidence. No visual generated; phrase/IP review remains separate. Дата: 2026-09-23 09:59:11.838032+00.
- **niche_fit**: 9.70 (confidence 0.742). Unified Forge diversity-v3 concept score grounded in current occupational tasks and niche evidence. No visual generated; phrase/IP review remains separate. Дата: 2026-09-23 09:59:11.838032+00.
- **visual_potential**: 9.70 (confidence 0.757). Unified Forge diversity-v3 concept score grounded in current occupational tasks and niche evidence. No visual generated; phrase/IP review remains separate. Дата: 2026-09-23 09:59:11.838032+00.

#### Ophthalmic tech — blink negotiation
`v4_oph_dont_blink` · ID `b87c7f16-b16c-445f-a5aa-8d80a501f8fe`

**Интерпретация:** Исследовательский кандидат; одобрение владельца не зафиксировано
**Статус БД:** scored · **балл:** 89.55 · **confidence:** 70.32 · **coverage:** 100.00
**Текст / хук:** I SAY 'DON'T BLINK' FOR A LIVING.
**Идея:** Turn the impossible request not to blink into a patient-interaction joke.
**Покупатель:** Ophthalmic medical technicians / assistants
**Причина покупки:** Simple social identity line with high coworker recognition.
**Отличие:** The phrase describes a recurring human interaction, not a workflow sequence.
**Визуальное направление:** Eye icon trying not to blink; clean, non-medical-claim visual.
**Создано / обновлено:** 2026-09-23 19:58:09.189566+00 / 2026-09-24 05:05:38.621539+00

Компоненты оценки:
- **buyer_desire**: 8.90 (confidence 0.700). purchase_trigger_v2 preliminary score; gate passed; trigger=patient_interaction_humor Дата: 2026-09-23 19:59:53.152527+00.
- **clarity_at_glance**: 9.30 (confidence 0.760). purchase_trigger_v2 preliminary score; gate passed; trigger=patient_interaction_humor Дата: 2026-09-23 19:59:53.152527+00.
- **distinctiveness**: 8.60 (confidence 0.700). purchase_trigger_v2 preliminary score; gate passed; trigger=patient_interaction_humor Дата: 2026-09-23 19:59:53.152527+00.
- **giftability**: 8.90 (confidence 0.670). purchase_trigger_v2 preliminary score; gate passed; trigger=patient_interaction_humor Дата: 2026-09-23 19:59:53.152527+00.
- **insider_resonance**: 9.30 (confidence 0.720). purchase_trigger_v2 preliminary score; gate passed; trigger=patient_interaction_humor Дата: 2026-09-23 19:59:53.152527+00.
- **ip_safety**: 8.90 (confidence 0.600). purchase_trigger_v2 preliminary score; gate passed; trigger=patient_interaction_humor Дата: 2026-09-23 19:59:53.152527+00.
- **niche_fit**: 9.30 (confidence 0.720). purchase_trigger_v2 preliminary score; gate passed; trigger=patient_interaction_humor Дата: 2026-09-23 19:59:53.152527+00.
- **visual_potential**: 8.80 (confidence 0.720). purchase_trigger_v2 preliminary score; gate passed; trigger=patient_interaction_humor Дата: 2026-09-23 19:59:53.152527+00.

#### Ophthalmic tech — professional flinch negotiator
`v4_oph_flinch_negotiator` · ID `6378a77a-706c-4b3d-a7b2-ee603fcc1e71`

**Интерпретация:** V4: понижен редакционным отбором, сохранен в истории
**Статус БД:** scored · **балл:** 85.66 · **confidence:** 70.32 · **coverage:** 100.00
**Текст / хук:** PROFESSIONAL FLINCH NEGOTIATOR.
**Идея:** Identity joke about coaching nervous patients through eye tests.
**Покупатель:** Ophthalmic medical technicians / assistants
**Причина покупки:** Humor + pride in the social skill of making testing possible.
**Отличие:** Not tied to a branded test or list of procedures.
**Визуальное направление:** Two cartoon eyes leaning away while a calm tech coaxes them back.
**editorial_reason:** professional flinch is established negotiation terminology
**Создано / обновлено:** 2026-09-23 19:58:09.189566+00 / 2026-09-24 05:05:38.621539+00

Компоненты оценки:
- **buyer_desire**: 8.40 (confidence 0.700). purchase_trigger_v2 preliminary score; gate passed; trigger=social_skill_pride Дата: 2026-09-23 19:59:53.152527+00.
- **clarity_at_glance**: 8.90 (confidence 0.760). purchase_trigger_v2 preliminary score; gate passed; trigger=social_skill_pride Дата: 2026-09-23 19:59:53.152527+00.
- **distinctiveness**: 8.30 (confidence 0.700). purchase_trigger_v2 preliminary score; gate passed; trigger=social_skill_pride Дата: 2026-09-23 19:59:53.152527+00.
- **giftability**: 8.20 (confidence 0.670). purchase_trigger_v2 preliminary score; gate passed; trigger=social_skill_pride Дата: 2026-09-23 19:59:53.152527+00.
- **insider_resonance**: 8.80 (confidence 0.720). purchase_trigger_v2 preliminary score; gate passed; trigger=social_skill_pride Дата: 2026-09-23 19:59:53.152527+00.
- **ip_safety**: 8.90 (confidence 0.600). purchase_trigger_v2 preliminary score; gate passed; trigger=social_skill_pride Дата: 2026-09-23 19:59:53.152527+00.
- **niche_fit**: 9.20 (confidence 0.720). purchase_trigger_v2 preliminary score; gate passed; trigger=social_skill_pride Дата: 2026-09-23 19:59:53.152527+00.
- **visual_potential**: 8.70 (confidence 0.720). purchase_trigger_v2 preliminary score; gate passed; trigger=social_skill_pride Дата: 2026-09-23 19:59:53.152527+00.

#### Ophthalmic tech — no air puff reassurance
`v4_oph_no_puff` · ID `f8e732b9-739f-4709-96fc-c2ebd14caab1`

**Интерпретация:** Исследовательский кандидат; одобрение владельца не зафиксировано
**Статус БД:** scored · **балл:** 90.33 · **confidence:** 70.32 · **coverage:** 100.00
**Текст / хук:** NO, THIS ONE DOESN'T PUFF AIR.
**Идея:** Make the endlessly repeated patient question the center of the joke.
**Покупатель:** Ophthalmic medical technicians / assistants
**Причина покупки:** Instant shared-clinic humor and giftability for eye-care staff.
**Отличие:** The joke is repeated patient behavior, not the device name.
**Визуальное направление:** Friendly machine silhouette with a crossed-out puff cloud.
**Создано / обновлено:** 2026-09-23 19:58:09.189566+00 / 2026-09-24 05:05:38.621539+00

Компоненты оценки:
- **buyer_desire**: 9.00 (confidence 0.700). purchase_trigger_v2 preliminary score; gate passed; trigger=patient_interaction_humor Дата: 2026-09-23 19:59:53.152527+00.
- **clarity_at_glance**: 9.40 (confidence 0.760). purchase_trigger_v2 preliminary score; gate passed; trigger=patient_interaction_humor Дата: 2026-09-23 19:59:53.152527+00.
- **distinctiveness**: 8.70 (confidence 0.700). purchase_trigger_v2 preliminary score; gate passed; trigger=patient_interaction_humor Дата: 2026-09-23 19:59:53.152527+00.
- **giftability**: 9.00 (confidence 0.670). purchase_trigger_v2 preliminary score; gate passed; trigger=patient_interaction_humor Дата: 2026-09-23 19:59:53.152527+00.
- **insider_resonance**: 9.40 (confidence 0.720). purchase_trigger_v2 preliminary score; gate passed; trigger=patient_interaction_humor Дата: 2026-09-23 19:59:53.152527+00.
- **ip_safety**: 8.90 (confidence 0.600). purchase_trigger_v2 preliminary score; gate passed; trigger=patient_interaction_humor Дата: 2026-09-23 19:59:53.152527+00.
- **niche_fit**: 9.30 (confidence 0.720). purchase_trigger_v2 preliminary score; gate passed; trigger=patient_interaction_humor Дата: 2026-09-23 19:59:53.152527+00.
- **visual_potential**: 8.80 (confidence 0.720). purchase_trigger_v2 preliminary score; gate passed; trigger=patient_interaction_humor Дата: 2026-09-23 19:59:53.152527+00.

#### Ophthalmic tech — eye-test whisperer
`v4_oph_patient_whisperer` · ID `6e97f507-9826-4126-928d-957173b731ed`

**Интерпретация:** V4: понижен редакционным отбором, сохранен в истории
**Статус БД:** scored · **балл:** 82.74 · **confidence:** 70.32 · **coverage:** 100.00
**Текст / хук:** EYE TEST WHISPERER.
**Идея:** Pride concept focused on calm patient handling rather than equipment knowledge.
**Покупатель:** Ophthalmic medical technicians / assistants
**Причина покупки:** Giftable identity with a human-facing skill at the center.
**Отличие:** The wearer is defined by social competence, not job vocabulary.
**Визуальное направление:** Calm speech bubble guiding a nervous cartoon eye.
**editorial_reason:** generic whisperer formula
**Создано / обновлено:** 2026-09-23 19:58:09.189566+00 / 2026-09-24 05:05:38.621539+00

Компоненты оценки:
- **buyer_desire**: 8.00 (confidence 0.700). purchase_trigger_v2 preliminary score; gate passed; trigger=care_skill_pride Дата: 2026-09-23 19:59:53.152527+00.
- **clarity_at_glance**: 8.80 (confidence 0.760). purchase_trigger_v2 preliminary score; gate passed; trigger=care_skill_pride Дата: 2026-09-23 19:59:53.152527+00.
- **distinctiveness**: 7.70 (confidence 0.700). purchase_trigger_v2 preliminary score; gate passed; trigger=care_skill_pride Дата: 2026-09-23 19:59:53.152527+00.
- **giftability**: 8.00 (confidence 0.670). purchase_trigger_v2 preliminary score; gate passed; trigger=care_skill_pride Дата: 2026-09-23 19:59:53.152527+00.
- **insider_resonance**: 8.60 (confidence 0.720). purchase_trigger_v2 preliminary score; gate passed; trigger=care_skill_pride Дата: 2026-09-23 19:59:53.152527+00.
- **ip_safety**: 8.90 (confidence 0.600). purchase_trigger_v2 preliminary score; gate passed; trigger=care_skill_pride Дата: 2026-09-23 19:59:53.152527+00.
- **niche_fit**: 9.20 (confidence 0.720). purchase_trigger_v2 preliminary score; gate passed; trigger=care_skill_pride Дата: 2026-09-23 19:59:53.152527+00.
- **visual_potential**: 8.50 (confidence 0.720). purchase_trigger_v2 preliminary score; gate passed; trigger=care_skill_pride Дата: 2026-09-23 19:59:53.152527+00.

#### Ophthalmic tech — same question all day
`v4_oph_same_question` · ID `bbdd6495-1ad2-4104-a0a2-1385e51e77c3`

**Интерпретация:** Исследовательский кандидат; одобрение владельца не зафиксировано
**Статус БД:** scored · **балл:** 87.08 · **confidence:** 70.32 · **coverage:** 100.00
**Текст / хук:** YES, SOMEONE ALREADY ASKED IF IT'S THE AIR PUFF.
**Идея:** A general clinic inside joke about hearing the air-puff question dozens of times.
**Покупатель:** Ophthalmic medical technicians / assistants
**Причина покупки:** Relatable repetition humor for staff gifts.
**Отличие:** The hook is human repetition, not terminology.
**Визуальное направление:** Tally marks around a small puff cloud / speech bubble.
**Создано / обновлено:** 2026-09-23 19:58:09.189566+00 / 2026-09-24 05:05:38.621539+00

Компоненты оценки:
- **buyer_desire**: 8.60 (confidence 0.700). purchase_trigger_v2 preliminary score; gate passed; trigger=repetition_humor Дата: 2026-09-23 19:59:53.152527+00.
- **clarity_at_glance**: 9.10 (confidence 0.760). purchase_trigger_v2 preliminary score; gate passed; trigger=repetition_humor Дата: 2026-09-23 19:59:53.152527+00.
- **distinctiveness**: 8.30 (confidence 0.700). purchase_trigger_v2 preliminary score; gate passed; trigger=repetition_humor Дата: 2026-09-23 19:59:53.152527+00.
- **giftability**: 8.70 (confidence 0.670). purchase_trigger_v2 preliminary score; gate passed; trigger=repetition_humor Дата: 2026-09-23 19:59:53.152527+00.
- **insider_resonance**: 9.10 (confidence 0.720). purchase_trigger_v2 preliminary score; gate passed; trigger=repetition_humor Дата: 2026-09-23 19:59:53.152527+00.
- **ip_safety**: 8.90 (confidence 0.600). purchase_trigger_v2 preliminary score; gate passed; trigger=repetition_humor Дата: 2026-09-23 19:59:53.152527+00.
- **niche_fit**: 9.10 (confidence 0.720). purchase_trigger_v2 preliminary score; gate passed; trigger=repetition_humor Дата: 2026-09-23 19:59:53.152527+00.
- **visual_potential**: 8.50 (confidence 0.720). purchase_trigger_v2 preliminary score; gate passed; trigger=repetition_humor Дата: 2026-09-23 19:59:53.152527+00.

## 34. Orthotist / Prosthetist
Ключ: `orthotist_prosthetist` · ID: `84d64709-8e51-4681-ae9a-df1d651b603e`

**Статус БД:** scored · **балл:** 75.65 · **confidence:** 78.46 · **coverage:** 100.00
**Аудитория:** Certified orthotists, prosthetists and O&P clinicians
**Категория:** occupational_identity
**Исследовательская аргументация:** Tiny but fast-growing design-and-fabrication profession with extraordinary visual and process depth: measure, model, fabricate, align, fit, gait. Etsy has 33+ to 51+ dedicated O&P shirt items, including many generic/fandom parody designs.
**Создано / обновлено:** 2026-09-23 09:42:54.27545+00 / 2026-09-23 09:43:36.792084+00

### Компоненты оценки ниши

- **channel_breadth**: 8.00 (confidence 0.640). Forge hidden-trades v2 initial score using current BLS/O*NET occupational evidence plus sampled Etsy marketplace depth. Scores prioritize buyer identity and whitespace, not raw occupation size. Benchmark niches intentionally receive competition penalties. Дата: 2026-09-23 09:43:36.792084+00.
- **competition_opportunity**: 5.50 (confidence 0.840). Forge hidden-trades v2 initial score using current BLS/O*NET occupational evidence plus sampled Etsy marketplace depth. Scores prioritize buyer identity and whitespace, not raw occupation size. Benchmark niches intentionally receive competition penalties. Дата: 2026-09-23 09:43:36.792084+00.
- **concept_depth**: 10.00 (confidence 0.840). Forge hidden-trades v2 initial score using current BLS/O*NET occupational evidence plus sampled Etsy marketplace depth. Scores prioritize buyer identity and whitespace, not raw occupation size. Benchmark niches intentionally receive competition penalties. Дата: 2026-09-23 09:43:36.792084+00.
- **demand_evidence**: 5.50 (confidence 0.880). Forge hidden-trades v2 initial score using current BLS/O*NET occupational evidence plus sampled Etsy marketplace depth. Scores prioritize buyer identity and whitespace, not raw occupation size. Benchmark niches intentionally receive competition penalties. Дата: 2026-09-23 09:43:36.792084+00.
- **founder_edge**: 2.00 (confidence 0.400). Forge hidden-trades v2 initial score using current BLS/O*NET occupational evidence plus sampled Etsy marketplace depth. Scores prioritize buyer identity and whitespace, not raw occupation size. Benchmark niches intentionally receive competition penalties. Дата: 2026-09-23 09:43:36.792084+00.
- **identity_intensity**: 9.00 (confidence 0.760). Forge hidden-trades v2 initial score using current BLS/O*NET occupational evidence plus sampled Etsy marketplace depth. Scores prioritize buyer identity and whitespace, not raw occupation size. Benchmark niches intentionally receive competition penalties. Дата: 2026-09-23 09:43:36.792084+00.
- **legal_safety**: 7.50 (confidence 0.580). Forge hidden-trades v2 initial score using current BLS/O*NET occupational evidence plus sampled Etsy marketplace depth. Scores prioritize buyer identity and whitespace, not raw occupation size. Benchmark niches intentionally receive competition penalties. Дата: 2026-09-23 09:43:36.792084+00.
- **purchase_motivation**: 8.00 (confidence 0.700). Forge hidden-trades v2 initial score using current BLS/O*NET occupational evidence plus sampled Etsy marketplace depth. Scores prioritize buyer identity and whitespace, not raw occupation size. Benchmark niches intentionally receive competition penalties. Дата: 2026-09-23 09:43:36.792084+00.
- **repeatability**: 8.50 (confidence 0.700). Forge hidden-trades v2 initial score using current BLS/O*NET occupational evidence plus sampled Etsy marketplace depth. Scores prioritize buyer identity and whitespace, not raw occupation size. Benchmark niches intentionally receive competition penalties. Дата: 2026-09-23 09:43:36.792084+00.
- **visual_language**: 10.00 (confidence 0.880). Forge hidden-trades v2 initial score using current BLS/O*NET occupational evidence plus sampled Etsy marketplace depth. Scores prioritize buyer identity and whitespace, not raw occupation size. Benchmark niches intentionally receive competition penalties. Дата: 2026-09-23 09:43:36.792084+00.

### Концепции (0)

## 35. Electrical Power-Line Installer / Repairer
Ключ: `power_line_installer_repairer` · ID: `18dbdecd-a0e4-4770-b976-090db1ca08b8`

**Статус БД:** scored · **балл:** 73.45 · **confidence:** 80.20 · **coverage:** 100.00
**Аудитория:** Power-line installers, repairers, journeymen linemen and apprentices
**Категория:** occupational_identity
**Исследовательская аргументация:** Excellent demand and identity, but marketplace is clearly saturated. Retained as a benchmark so Forge does not confuse large occupational demand with whitespace.
**Создано / обновлено:** 2026-09-23 09:34:00.70472+00 / 2026-09-23 09:34:30.438105+00

### Компоненты оценки ниши

- **channel_breadth**: 8.00 (confidence 0.700). Initial evidence-weighted Forge score from current BLS/O*NET data, sampled Etsy competition and practitioner-community signals. See niche_candidates.source_notes. This is prioritization research, not a sales forecast. Дата: 2026-09-23 09:34:30.438105+00.
- **competition_opportunity**: 1.50 (confidence 0.900). Initial evidence-weighted Forge score from current BLS/O*NET data, sampled Etsy competition and practitioner-community signals. See niche_candidates.source_notes. This is prioritization research, not a sales forecast. Дата: 2026-09-23 09:34:30.438105+00.
- **concept_depth**: 7.00 (confidence 0.700). Initial evidence-weighted Forge score from current BLS/O*NET data, sampled Etsy competition and practitioner-community signals. See niche_candidates.source_notes. This is prioritization research, not a sales forecast. Дата: 2026-09-23 09:34:30.438105+00.
- **demand_evidence**: 9.00 (confidence 0.900). Initial evidence-weighted Forge score from current BLS/O*NET data, sampled Etsy competition and practitioner-community signals. See niche_candidates.source_notes. This is prioritization research, not a sales forecast. Дата: 2026-09-23 09:34:30.438105+00.
- **founder_edge**: 3.00 (confidence 0.400). Initial evidence-weighted Forge score from current BLS/O*NET data, sampled Etsy competition and practitioner-community signals. See niche_candidates.source_notes. This is prioritization research, not a sales forecast. Дата: 2026-09-23 09:34:30.438105+00.
- **identity_intensity**: 9.00 (confidence 0.800). Initial evidence-weighted Forge score from current BLS/O*NET data, sampled Etsy competition and practitioner-community signals. See niche_candidates.source_notes. This is prioritization research, not a sales forecast. Дата: 2026-09-23 09:34:30.438105+00.
- **legal_safety**: 8.00 (confidence 0.700). Initial evidence-weighted Forge score from current BLS/O*NET data, sampled Etsy competition and practitioner-community signals. See niche_candidates.source_notes. This is prioritization research, not a sales forecast. Дата: 2026-09-23 09:34:30.438105+00.
- **purchase_motivation**: 9.00 (confidence 0.800). Initial evidence-weighted Forge score from current BLS/O*NET data, sampled Etsy competition and practitioner-community signals. See niche_candidates.source_notes. This is prioritization research, not a sales forecast. Дата: 2026-09-23 09:34:30.438105+00.
- **repeatability**: 8.00 (confidence 0.700). Initial evidence-weighted Forge score from current BLS/O*NET data, sampled Etsy competition and practitioner-community signals. See niche_candidates.source_notes. This is prioritization research, not a sales forecast. Дата: 2026-09-23 09:34:30.438105+00.
- **visual_language**: 8.50 (confidence 0.800). Initial evidence-weighted Forge score from current BLS/O*NET data, sampled Etsy competition and practitioner-community signals. See niche_candidates.source_notes. This is prioritization research, not a sales forecast. Дата: 2026-09-23 09:34:30.438105+00.

### Концепции (0)

## 36. Power Plant / Control Room Operator
Ключ: `power_plant_operator` · ID: `2a3cb67b-e59b-4207-bf14-2e39a9767582`

**Статус БД:** scored · **балл:** 77.75 · **confidence:** 67.07 · **coverage:** 100.00
**Аудитория:** Power plant operators and control-room operators
**Категория:** occupational_identity
**Исследовательская аргументация:** High-skill control-room occupation with strong systems language around generation, voltage, flow, turbines, generators and alarms. Total employment is declining, but replacement openings remain and visual/identity depth is high.
**Создано / обновлено:** 2026-09-23 09:42:54.27545+00 / 2026-09-23 09:43:36.792084+00

### Компоненты оценки ниши

- **channel_breadth**: 7.00 (confidence 0.550). Forge hidden-trades v2 initial score using current BLS/O*NET occupational evidence plus sampled Etsy marketplace depth. Scores prioritize buyer identity and whitespace, not raw occupation size. Benchmark niches intentionally receive competition penalties. Дата: 2026-09-23 09:43:36.792084+00.
- **competition_opportunity**: 8.50 (confidence 0.480). Forge hidden-trades v2 initial score using current BLS/O*NET occupational evidence plus sampled Etsy marketplace depth. Scores prioritize buyer identity and whitespace, not raw occupation size. Benchmark niches intentionally receive competition penalties. Дата: 2026-09-23 09:43:36.792084+00.
- **concept_depth**: 9.00 (confidence 0.720). Forge hidden-trades v2 initial score using current BLS/O*NET occupational evidence plus sampled Etsy marketplace depth. Scores prioritize buyer identity and whitespace, not raw occupation size. Benchmark niches intentionally receive competition penalties. Дата: 2026-09-23 09:43:36.792084+00.
- **demand_evidence**: 6.00 (confidence 0.860). Forge hidden-trades v2 initial score using current BLS/O*NET occupational evidence plus sampled Etsy marketplace depth. Scores prioritize buyer identity and whitespace, not raw occupation size. Benchmark niches intentionally receive competition penalties. Дата: 2026-09-23 09:43:36.792084+00.
- **founder_edge**: 2.00 (confidence 0.400). Forge hidden-trades v2 initial score using current BLS/O*NET occupational evidence plus sampled Etsy marketplace depth. Scores prioritize buyer identity and whitespace, not raw occupation size. Benchmark niches intentionally receive competition penalties. Дата: 2026-09-23 09:43:36.792084+00.
- **identity_intensity**: 8.50 (confidence 0.680). Forge hidden-trades v2 initial score using current BLS/O*NET occupational evidence plus sampled Etsy marketplace depth. Scores prioritize buyer identity and whitespace, not raw occupation size. Benchmark niches intentionally receive competition penalties. Дата: 2026-09-23 09:43:36.792084+00.
- **legal_safety**: 9.00 (confidence 0.680). Forge hidden-trades v2 initial score using current BLS/O*NET occupational evidence plus sampled Etsy marketplace depth. Scores prioritize buyer identity and whitespace, not raw occupation size. Benchmark niches intentionally receive competition penalties. Дата: 2026-09-23 09:43:36.792084+00.
- **purchase_motivation**: 7.50 (confidence 0.600). Forge hidden-trades v2 initial score using current BLS/O*NET occupational evidence plus sampled Etsy marketplace depth. Scores prioritize buyer identity and whitespace, not raw occupation size. Benchmark niches intentionally receive competition penalties. Дата: 2026-09-23 09:43:36.792084+00.
- **repeatability**: 8.00 (confidence 0.600). Forge hidden-trades v2 initial score using current BLS/O*NET occupational evidence plus sampled Etsy marketplace depth. Scores prioritize buyer identity and whitespace, not raw occupation size. Benchmark niches intentionally receive competition penalties. Дата: 2026-09-23 09:43:36.792084+00.
- **visual_language**: 9.50 (confidence 0.780). Forge hidden-trades v2 initial score using current BLS/O*NET occupational evidence plus sampled Etsy marketplace depth. Scores prioritize buyer identity and whitespace, not raw occupation size. Benchmark niches intentionally receive competition penalties. Дата: 2026-09-23 09:43:36.792084+00.

### Концепции (0)

## 37. Radiation Therapist
Ключ: `radiation_therapist` · ID: `17d703f9-6abd-4831-9c85-b79641ed3a03`

**Статус БД:** scored · **балл:** 77.05 · **confidence:** 78.26 · **coverage:** 100.00
**Аудитория:** Radiation therapists in oncology treatment teams
**Категория:** occupational_identity
**Исследовательская аргументация:** Small high-skill cancer-treatment occupation with strong beam, setup, treatment-plan and verification visual language. Marketplace is clearly established, so opportunity depends on technical insider concepts rather than generic job-title/floral merch.
**Создано / обновлено:** 2026-09-23 09:56:40.513406+00 / 2026-09-23 23:52:40.297494+00

### Компоненты оценки ниши

- **channel_breadth**: 7.50 (confidence 0.600). Forge diversity-batch v3 score using current 2025-35 BLS/O*NET evidence plus sampled current Etsy competition. Where exact marketplace counts were unavailable, competition confidence is intentionally lower. Дата: 2026-09-23 09:56:40.513406+00.
- **competition_opportunity**: 6.00 (confidence 0.840). Forge diversity-batch v3 score using current 2025-35 BLS/O*NET evidence plus sampled current Etsy competition. Where exact marketplace counts were unavailable, competition confidence is intentionally lower. Дата: 2026-09-23 09:56:40.513406+00.
- **concept_depth**: 9.50 (confidence 0.820). Forge diversity-batch v3 score using current 2025-35 BLS/O*NET evidence plus sampled current Etsy competition. Where exact marketplace counts were unavailable, competition confidence is intentionally lower. Дата: 2026-09-23 09:56:40.513406+00.
- **demand_evidence**: 6.50 (confidence 0.900). Forge diversity-batch v3 score using current 2025-35 BLS/O*NET evidence plus sampled current Etsy competition. Where exact marketplace counts were unavailable, competition confidence is intentionally lower. Дата: 2026-09-23 09:56:40.513406+00.
- **founder_edge**: 2.00 (confidence 0.400). Forge diversity-batch v3 score using current 2025-35 BLS/O*NET evidence plus sampled current Etsy competition. Where exact marketplace counts were unavailable, competition confidence is intentionally lower. Дата: 2026-09-23 09:56:40.513406+00.
- **identity_intensity**: 9.00 (confidence 0.780). Forge diversity-batch v3 score using current 2025-35 BLS/O*NET evidence plus sampled current Etsy competition. Where exact marketplace counts were unavailable, competition confidence is intentionally lower. Дата: 2026-09-23 09:56:40.513406+00.
- **legal_safety**: 8.00 (confidence 0.600). Forge diversity-batch v3 score using current 2025-35 BLS/O*NET evidence plus sampled current Etsy competition. Where exact marketplace counts were unavailable, competition confidence is intentionally lower. Дата: 2026-09-23 09:56:40.513406+00.
- **purchase_motivation**: 8.00 (confidence 0.700). Forge diversity-batch v3 score using current 2025-35 BLS/O*NET evidence plus sampled current Etsy competition. Where exact marketplace counts were unavailable, competition confidence is intentionally lower. Дата: 2026-09-23 09:56:40.513406+00.
- **repeatability**: 8.00 (confidence 0.660). Forge diversity-batch v3 score using current 2025-35 BLS/O*NET evidence plus sampled current Etsy competition. Where exact marketplace counts were unavailable, competition confidence is intentionally lower. Дата: 2026-09-23 09:56:40.513406+00.
- **visual_language**: 9.50 (confidence 0.840). Forge diversity-batch v3 score using current 2025-35 BLS/O*NET evidence plus sampled current Etsy competition. Where exact marketplace counts were unavailable, competition confidence is intentionally lower. Дата: 2026-09-23 09:56:40.513406+00.

### Концепции (0)

## 38. Rail Signal Maintainer / Signal & Track Switch Repairer
Ключ: `rail_signal_maintainer` · ID: `fd5e41f3-0015-42b1-8b3d-7f3809610833`

**Статус БД:** scored · **балл:** 77.45 · **confidence:** 66.52 · **coverage:** 100.00
**Аудитория:** Railroad signal maintainers and signal/track-switch repairers
**Категория:** occupational_identity
**Исследовательская аргументация:** Very small rail-systems trade with distinctive signal circuits, interlockings, crossings, relays and track-switch visual language. Strong insider specificity but limited audience size.
**Создано / обновлено:** 2026-09-23 10:00:20.805089+00 / 2026-09-23 10:04:52.652496+00

### Компоненты оценки ниши

- **channel_breadth**: 6.50 (confidence 0.500). Forge pool-completion provisional score using current BLS/O*NET evidence and sampled Etsy competition. Lower confidence is intentional where exact employment sizing or clean marketplace decomposition is unavailable. Дата: 2026-09-23 10:04:52.652496+00.
- **competition_opportunity**: 9.00 (confidence 0.500). Forge pool-completion provisional score using current BLS/O*NET evidence and sampled Etsy competition. Lower confidence is intentional where exact employment sizing or clean marketplace decomposition is unavailable. Дата: 2026-09-23 10:04:52.652496+00.
- **concept_depth**: 9.50 (confidence 0.700). Forge pool-completion provisional score using current BLS/O*NET evidence and sampled Etsy competition. Lower confidence is intentional where exact employment sizing or clean marketplace decomposition is unavailable. Дата: 2026-09-23 10:04:52.652496+00.
- **demand_evidence**: 5.50 (confidence 0.880). Forge pool-completion provisional score using current BLS/O*NET evidence and sampled Etsy competition. Lower confidence is intentional where exact employment sizing or clean marketplace decomposition is unavailable. Дата: 2026-09-23 10:04:52.652496+00.
- **founder_edge**: 2.00 (confidence 0.400). Forge pool-completion provisional score using current BLS/O*NET evidence and sampled Etsy competition. Lower confidence is intentional where exact employment sizing or clean marketplace decomposition is unavailable. Дата: 2026-09-23 10:04:52.652496+00.
- **identity_intensity**: 8.50 (confidence 0.680). Forge pool-completion provisional score using current BLS/O*NET evidence and sampled Etsy competition. Lower confidence is intentional where exact employment sizing or clean marketplace decomposition is unavailable. Дата: 2026-09-23 10:04:52.652496+00.
- **legal_safety**: 8.50 (confidence 0.600). Forge pool-completion provisional score using current BLS/O*NET evidence and sampled Etsy competition. Lower confidence is intentional where exact employment sizing or clean marketplace decomposition is unavailable. Дата: 2026-09-23 10:04:52.652496+00.
- **purchase_motivation**: 7.50 (confidence 0.600). Forge pool-completion provisional score using current BLS/O*NET evidence and sampled Etsy competition. Lower confidence is intentional where exact employment sizing or clean marketplace decomposition is unavailable. Дата: 2026-09-23 10:04:52.652496+00.
- **repeatability**: 7.50 (confidence 0.560). Forge pool-completion provisional score using current BLS/O*NET evidence and sampled Etsy competition. Lower confidence is intentional where exact employment sizing or clean marketplace decomposition is unavailable. Дата: 2026-09-23 10:04:52.652496+00.
- **visual_language**: 9.50 (confidence 0.740). Forge pool-completion provisional score using current BLS/O*NET evidence and sampled Etsy competition. Lower confidence is intentional where exact employment sizing or clean marketplace decomposition is unavailable. Дата: 2026-09-23 10:04:52.652496+00.

### Концепции (0)

## 39. Refinery / Petroleum Pump System Operator
Ключ: `refinery_operator` · ID: `7369723c-aa8a-4e42-95d0-ff2a8485b370`

**Статус БД:** scored · **балл:** 73.45 · **confidence:** 70.92 · **coverage:** 100.00
**Аудитория:** Refinery operators, petroleum pump-system operators and gaugers
**Категория:** occupational_identity
**Исследовательская аргументация:** Process-industry identity with strong equipment/flow/control-room language and a nontrivial but still bounded merch market. Audience is modest and slightly declining.
**Создано / обновлено:** 2026-09-23 10:00:20.805089+00 / 2026-09-23 10:04:52.652496+00

### Компоненты оценки ниши

- **channel_breadth**: 7.00 (confidence 0.540). Forge pool-completion provisional score using current BLS/O*NET evidence and sampled Etsy competition. Lower confidence is intentional where exact employment sizing or clean marketplace decomposition is unavailable. Дата: 2026-09-23 10:04:52.652496+00.
- **competition_opportunity**: 6.50 (confidence 0.780). Forge pool-completion provisional score using current BLS/O*NET evidence and sampled Etsy competition. Lower confidence is intentional where exact employment sizing or clean marketplace decomposition is unavailable. Дата: 2026-09-23 10:04:52.652496+00.
- **concept_depth**: 9.00 (confidence 0.680). Forge pool-completion provisional score using current BLS/O*NET evidence and sampled Etsy competition. Lower confidence is intentional where exact employment sizing or clean marketplace decomposition is unavailable. Дата: 2026-09-23 10:04:52.652496+00.
- **demand_evidence**: 6.20 (confidence 0.880). Forge pool-completion provisional score using current BLS/O*NET evidence and sampled Etsy competition. Lower confidence is intentional where exact employment sizing or clean marketplace decomposition is unavailable. Дата: 2026-09-23 10:04:52.652496+00.
- **founder_edge**: 2.00 (confidence 0.400). Forge pool-completion provisional score using current BLS/O*NET evidence and sampled Etsy competition. Lower confidence is intentional where exact employment sizing or clean marketplace decomposition is unavailable. Дата: 2026-09-23 10:04:52.652496+00.
- **identity_intensity**: 8.00 (confidence 0.680). Forge pool-completion provisional score using current BLS/O*NET evidence and sampled Etsy competition. Lower confidence is intentional where exact employment sizing or clean marketplace decomposition is unavailable. Дата: 2026-09-23 10:04:52.652496+00.
- **legal_safety**: 8.00 (confidence 0.600). Forge pool-completion provisional score using current BLS/O*NET evidence and sampled Etsy competition. Lower confidence is intentional where exact employment sizing or clean marketplace decomposition is unavailable. Дата: 2026-09-23 10:04:52.652496+00.
- **purchase_motivation**: 7.50 (confidence 0.620). Forge pool-completion provisional score using current BLS/O*NET evidence and sampled Etsy competition. Lower confidence is intentional where exact employment sizing or clean marketplace decomposition is unavailable. Дата: 2026-09-23 10:04:52.652496+00.
- **repeatability**: 7.50 (confidence 0.580). Forge pool-completion provisional score using current BLS/O*NET evidence and sampled Etsy competition. Lower confidence is intentional where exact employment sizing or clean marketplace decomposition is unavailable. Дата: 2026-09-23 10:04:52.652496+00.
- **visual_language**: 9.00 (confidence 0.720). Forge pool-completion provisional score using current BLS/O*NET evidence and sampled Etsy competition. Lower confidence is intentional where exact employment sizing or clean marketplace decomposition is unavailable. Дата: 2026-09-23 10:04:52.652496+00.

### Концепции (0)

## 40. Respiratory Therapist
Ключ: `respiratory_therapist` · ID: `a0c54b9c-945d-4c74-99b1-e865132bd23c`

**Статус БД:** scored · **балл:** 76.20 · **confidence:** 82.38 · **coverage:** 100.00
**Аудитория:** Respiratory therapists / RT / RRT professionals
**Категория:** occupational_identity
**Исследовательская аргументация:** Large and fast-growing profession with very strong identity, but current Etsy is massively saturated. Retained as a benchmark showing why high demand alone is not enough.
**Создано / обновлено:** 2026-09-23 09:56:40.513406+00 / 2026-09-23 09:56:40.513406+00

### Компоненты оценки ниши

- **channel_breadth**: 8.00 (confidence 0.660). Forge diversity-batch v3 score using current 2025-35 BLS/O*NET evidence plus sampled current Etsy competition. Where exact marketplace counts were unavailable, competition confidence is intentionally lower. Дата: 2026-09-23 09:56:40.513406+00.
- **competition_opportunity**: 1.00 (confidence 0.960). Forge diversity-batch v3 score using current 2025-35 BLS/O*NET evidence plus sampled current Etsy competition. Where exact marketplace counts were unavailable, competition confidence is intentionally lower. Дата: 2026-09-23 09:56:40.513406+00.
- **concept_depth**: 8.50 (confidence 0.740). Forge diversity-batch v3 score using current 2025-35 BLS/O*NET evidence plus sampled current Etsy competition. Where exact marketplace counts were unavailable, competition confidence is intentionally lower. Дата: 2026-09-23 09:56:40.513406+00.
- **demand_evidence**: 9.50 (confidence 0.940). Forge diversity-batch v3 score using current 2025-35 BLS/O*NET evidence plus sampled current Etsy competition. Where exact marketplace counts were unavailable, competition confidence is intentionally lower. Дата: 2026-09-23 09:56:40.513406+00.
- **founder_edge**: 2.00 (confidence 0.400). Forge diversity-batch v3 score using current 2025-35 BLS/O*NET evidence plus sampled current Etsy competition. Where exact marketplace counts were unavailable, competition confidence is intentionally lower. Дата: 2026-09-23 09:56:40.513406+00.
- **identity_intensity**: 9.00 (confidence 0.820). Forge diversity-batch v3 score using current 2025-35 BLS/O*NET evidence plus sampled current Etsy competition. Where exact marketplace counts were unavailable, competition confidence is intentionally lower. Дата: 2026-09-23 09:56:40.513406+00.
- **legal_safety**: 8.00 (confidence 0.620). Forge diversity-batch v3 score using current 2025-35 BLS/O*NET evidence plus sampled current Etsy competition. Where exact marketplace counts were unavailable, competition confidence is intentionally lower. Дата: 2026-09-23 09:56:40.513406+00.
- **purchase_motivation**: 9.00 (confidence 0.800). Forge diversity-batch v3 score using current 2025-35 BLS/O*NET evidence plus sampled current Etsy competition. Where exact marketplace counts were unavailable, competition confidence is intentionally lower. Дата: 2026-09-23 09:56:40.513406+00.
- **repeatability**: 9.00 (confidence 0.760). Forge diversity-batch v3 score using current 2025-35 BLS/O*NET evidence plus sampled current Etsy competition. Where exact marketplace counts were unavailable, competition confidence is intentionally lower. Дата: 2026-09-23 09:56:40.513406+00.
- **visual_language**: 9.00 (confidence 0.780). Forge diversity-batch v3 score using current 2025-35 BLS/O*NET evidence plus sampled current Etsy competition. Where exact marketplace counts were unavailable, competition confidence is intentionally lower. Дата: 2026-09-23 09:56:40.513406+00.

### Концепции (0)

## 41. Semiconductor Processing Technician
Ключ: `semiconductor_processing_technician` · ID: `8c4df196-09cb-4ca9-aee4-63d578bf0b9a`

**Статус БД:** shortlisted · **балл:** 79.55 · **confidence:** 75.14 · **coverage:** 100.00
**Аудитория:** Cleanroom semiconductor processing / fab technicians
**Категория:** occupational_identity
**Исследовательская аргументация:** Growing U.S. fab workforce with distinctive cleanroom, wafer, process-step and equipment language. Marketplace appears thin in sampled exact searches, while technical visual depth is unusually high.
**Создано / обновлено:** 2026-09-23 09:42:54.27545+00 / 2026-09-23 10:14:18.633101+00

### Компоненты оценки ниши

- **channel_breadth**: 8.00 (confidence 0.720). Forge hidden-trades v2 initial score using current BLS/O*NET occupational evidence plus sampled Etsy marketplace depth. Scores prioritize buyer identity and whitespace, not raw occupation size. Benchmark niches intentionally receive competition penalties. Semiconductor manufacturing, equipment vendors/FSE roles and broader electronics-manufacturing culture improve channel breadth confidence. Дата: 2026-09-23 09:43:36.792084+00.
- **competition_opportunity**: 9.20 (confidence 0.660). Forge hidden-trades v2 initial score using current BLS/O*NET occupational evidence plus sampled Etsy marketplace depth. Scores prioritize buyer identity and whitespace, not raw occupation size. Benchmark niches intentionally receive competition penalties. Current Etsy surfaced a dedicated Semiconductor Technician wafer-fab cleanroom shirt, while surrounding results were mostly generic microchip/programmer designs; direct exact-occupation competition appears thin but is not exhaustively counted. Дата: 2026-09-23 09:43:36.792084+00.
- **concept_depth**: 9.00 (confidence 0.780). Forge hidden-trades v2 initial score using current BLS/O*NET occupational evidence plus sampled Etsy marketplace depth. Scores prioritize buyer identity and whitespace, not raw occupation size. Benchmark niches intentionally receive competition penalties. Official cleanroom/process role plus current industry discussions support distinct hooks around wafer lots, tools, cleanroom, process steps, metrology and equipment monitoring. Дата: 2026-09-23 09:43:36.792084+00.
- **demand_evidence**: 8.00 (confidence 0.950). Forge hidden-trades v2 initial score using current BLS/O*NET occupational evidence plus sampled Etsy marketplace depth. Scores prioritize buyer identity and whitespace, not raw occupation size. Benchmark niches intentionally receive competition penalties. BLS directly reports 31,200 semiconductor processing technicians in 2025, 8% projected growth through 2035 and about 3,400 openings/year, with demand tied to U.S. semiconductor investment. Дата: 2026-09-23 09:43:36.792084+00.
- **founder_edge**: 2.00 (confidence 0.400). Forge hidden-trades v2 initial score using current BLS/O*NET occupational evidence plus sampled Etsy marketplace depth. Scores prioritize buyer identity and whitespace, not raw occupation size. Benchmark niches intentionally receive competition penalties. Дата: 2026-09-23 09:43:36.792084+00.
- **identity_intensity**: 6.80 (confidence 0.720). Forge hidden-trades v2 initial score using current BLS/O*NET occupational evidence plus sampled Etsy marketplace depth. Scores prioritize buyer identity and whitespace, not raw occupation size. Benchmark niches intentionally receive competition penalties. Current 2026 semiconductor discussions confirm a distinct cleanroom/fab/operator/technician work culture, gowning constraints and hands-on equipment identity. Дата: 2026-09-23 09:43:36.792084+00.
- **legal_safety**: 8.50 (confidence 0.620). Forge hidden-trades v2 initial score using current BLS/O*NET occupational evidence plus sampled Etsy marketplace depth. Scores prioritize buyer identity and whitespace, not raw occupation size. Benchmark niches intentionally receive competition penalties. Дата: 2026-09-23 09:43:36.792084+00.
- **purchase_motivation**: 6.80 (confidence 0.640). Forge hidden-trades v2 initial score using current BLS/O*NET occupational evidence plus sampled Etsy marketplace depth. Scores prioritize buyer identity and whitespace, not raw occupation size. Benchmark niches intentionally receive competition penalties. Fab/cleanroom identity is real but direct merch-buying motivation is still only indirectly supported; confidence raised modestly. Дата: 2026-09-23 09:43:36.792084+00.
- **repeatability**: 8.00 (confidence 0.700). Forge hidden-trades v2 initial score using current BLS/O*NET occupational evidence plus sampled Etsy marketplace depth. Scores prioritize buyer identity and whitespace, not raw occupation size. Benchmark niches intentionally receive competition penalties. Multiple fab process/equipment/cleanroom subthemes support a series. Дата: 2026-09-23 09:43:36.792084+00.
- **visual_language**: 9.50 (confidence 0.840). Forge hidden-trades v2 initial score using current BLS/O*NET occupational evidence plus sampled Etsy marketplace depth. Scores prioritize buyer identity and whitespace, not raw occupation size. Benchmark niches intentionally receive competition penalties. Wafer, fab tool, chamber, metrology and cleanroom visual language is specific and strongly supported. Дата: 2026-09-23 09:43:36.792084+00.

### Концепции (11)

#### Semiconductor — cleanroom control
`semi_cleanroom_contamination_control` · ID `32194fc1-e2bb-49fc-8c8d-341e0cd1a9dc`

**Интерпретация:** Исследовательский кандидат; одобрение владельца не зафиксировано
**Статус БД:** scored · **балл:** 88.11 · **confidence:** 68.17 · **coverage:** 100.00
**Текст / хук:** CLEANROOM • PARTICLE • CONTROL
**Идея:** Semiconductor — cleanroom control. Core hook: CLEANROOM • PARTICLE • CONTROL. Wafer processing, cleanroom equipment, lot control, inspection and metrology. Execution must stay original and descriptive; avoid employer, OEM, certification-body, association and proprietary-interface branding.
**Покупатель:** Semiconductor processing / wafer fab technicians
**Причина покупки:** Identity purchase for semiconductor processing / wafer fab technicians who recognize the real workflow/systems language.
**Отличие:** Insider technical technical map direction intended to avoid generic profession-title, retro-badge, skull, flag, coffee and parody templates.
**Визуальное направление:** Cleanroom/wafer composition focused on contamination awareness, gowning silhouette and particle-control visual language.
**Создано / обновлено:** 2026-09-23 09:48:50.541446+00 / 2026-09-23 09:57:07.855981+00

Компоненты оценки:
- **buyer_desire**: 8.34 (confidence 0.670). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **clarity_at_glance**: 7.77 (confidence 0.670). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **distinctiveness**: 9.20 (confidence 0.670). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **giftability**: 7.47 (confidence 0.670). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **insider_resonance**: 9.30 (confidence 0.700). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **ip_safety**: 8.60 (confidence 0.670). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **niche_fit**: 9.33 (confidence 0.700). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **visual_potential**: 9.60 (confidence 0.700). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.

#### Semiconductor — process / measure / review / release
`semi_process_measure_review_release` · ID `a910ab7b-a3cc-4107-9a51-1114a87488bb`

**Интерпретация:** Исследовательский кандидат; одобрение владельца не зафиксировано
**Статус БД:** scored · **балл:** 85.60 · **confidence:** 67.17 · **coverage:** 100.00
**Текст / хук:** PROCESS • MEASURE • REVIEW • RELEASE
**Идея:** Semiconductor — process / measure / review / release. Core hook: PROCESS • MEASURE • REVIEW • RELEASE. Wafer processing, cleanroom equipment, lot control, inspection and metrology. Execution must stay original and descriptive; avoid employer, OEM, certification-body, association and proprietary-interface branding.
**Покупатель:** Semiconductor processing / wafer fab technicians
**Причина покупки:** Identity purchase for semiconductor processing / wafer fab technicians who recognize the real workflow/systems language.
**Отличие:** Insider technical workflow direction intended to avoid generic profession-title, retro-badge, skull, flag, coffee and parody templates.
**Визуальное направление:** Quality-gate workflow between generic process tool, metrology and lot disposition.
**Создано / обновлено:** 2026-09-23 09:48:50.541446+00 / 2026-09-23 09:55:40.114238+00

Компоненты оценки:
- **buyer_desire**: 8.24 (confidence 0.660). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **clarity_at_glance**: 9.17 (confidence 0.660). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **distinctiveness**: 8.40 (confidence 0.660). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **giftability**: 8.07 (confidence 0.660). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **insider_resonance**: 8.80 (confidence 0.690). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **ip_safety**: 9.00 (confidence 0.660). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **niche_fit**: 9.23 (confidence 0.690). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **visual_potential**: 8.40 (confidence 0.690). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.

#### Semiconductor — recipe / run / monitor / log
`semi_recipe_run_monitor_log` · ID `f5f25bac-1d1c-4897-9e97-570d419ed405`

**Интерпретация:** Исследовательский кандидат; одобрение владельца не зафиксировано
**Статус БД:** scored · **балл:** 85.60 · **confidence:** 67.17 · **coverage:** 100.00
**Текст / хук:** RECIPE • RUN • MONITOR • LOG
**Идея:** Semiconductor — recipe / run / monitor / log. Core hook: RECIPE • RUN • MONITOR • LOG. Wafer processing, cleanroom equipment, lot control, inspection and metrology. Execution must stay original and descriptive; avoid employer, OEM, certification-body, association and proprietary-interface branding.
**Покупатель:** Semiconductor processing / wafer fab technicians
**Причина покупки:** Identity purchase for semiconductor processing / wafer fab technicians who recognize the real workflow/systems language.
**Отличие:** Insider technical workflow direction intended to avoid generic profession-title, retro-badge, skull, flag, coffee and parody templates.
**Визуальное направление:** Fab process-control identity using a generic recipe block, chamber and lot record; no real tool UI.
**Создано / обновлено:** 2026-09-23 09:48:50.541446+00 / 2026-09-23 09:55:40.114238+00

Компоненты оценки:
- **buyer_desire**: 8.24 (confidence 0.660). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **clarity_at_glance**: 9.17 (confidence 0.660). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **distinctiveness**: 8.40 (confidence 0.660). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **giftability**: 8.07 (confidence 0.660). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **insider_resonance**: 8.80 (confidence 0.690). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **ip_safety**: 9.00 (confidence 0.660). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **niche_fit**: 9.23 (confidence 0.690). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **visual_potential**: 8.40 (confidence 0.690). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.

#### Semiconductor — vacuum / gas / RF
`semi_vacuum_gas_rf_process` · ID `82ce8879-fcad-4613-b057-dd93d494b479`

**Интерпретация:** Исследовательский кандидат; одобрение владельца не зафиксировано
**Статус БД:** scored · **балл:** 86.32 · **confidence:** 67.17 · **coverage:** 100.00
**Текст / хук:** VACUUM • GAS • RF • PROCESS
**Идея:** Semiconductor — vacuum / gas / RF. Core hook: VACUUM • GAS • RF • PROCESS. Wafer processing, cleanroom equipment, lot control, inspection and metrology. Execution must stay original and descriptive; avoid employer, OEM, certification-body, association and proprietary-interface branding.
**Покупатель:** Semiconductor processing / wafer fab technicians
**Причина покупки:** Identity purchase for semiconductor processing / wafer fab technicians who recognize the real workflow/systems language.
**Отличие:** Insider technical terminology direction intended to avoid generic profession-title, retro-badge, skull, flag, coffee and parody templates.
**Визуальное направление:** High-level process-equipment domains arranged around a generic chamber; no recipe values or operating instructions.
**Создано / обновлено:** 2026-09-23 09:48:50.541446+00 / 2026-09-23 09:55:40.114238+00

Компоненты оценки:
- **buyer_desire**: 7.94 (confidence 0.660). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **clarity_at_glance**: 9.23 (confidence 0.660). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **distinctiveness**: 8.40 (confidence 0.660). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **giftability**: 8.13 (confidence 0.660). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **insider_resonance**: 9.45 (confidence 0.690). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **ip_safety**: 8.80 (confidence 0.660). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **niche_fit**: 9.43 (confidence 0.690). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **visual_potential**: 8.45 (confidence 0.690). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.

#### Semiconductor — wafer process loop
`semi_wafer_clean_process_inspect` · ID `5af36c95-44e9-439d-ad9d-434302fddd8f`

**Интерпретация:** Исследовательский кандидат; одобрение владельца не зафиксировано
**Статус БД:** scored · **балл:** 87.70 · **confidence:** 68.17 · **coverage:** 100.00
**Текст / хук:** CLEAN • PROCESS • INSPECT
**Идея:** Semiconductor — wafer process loop. Core hook: CLEAN • PROCESS • INSPECT. Wafer processing, cleanroom equipment, lot control, inspection and metrology. Execution must stay original and descriptive; avoid employer, OEM, certification-body, association and proprietary-interface branding.
**Покупатель:** Semiconductor processing / wafer fab technicians
**Причина покупки:** Identity purchase for semiconductor processing / wafer fab technicians who recognize the real workflow/systems language.
**Отличие:** Insider technical process direction intended to avoid generic profession-title, retro-badge, skull, flag, coffee and parody templates.
**Визуальное направление:** Wafer-centered process loop with generic tool-chamber geometry and inspection optics.
**Создано / обновлено:** 2026-09-23 09:48:50.541446+00 / 2026-09-23 09:55:40.114238+00

Компоненты оценки:
- **buyer_desire**: 8.44 (confidence 0.670). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **clarity_at_glance**: 8.80 (confidence 0.670). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **distinctiveness**: 8.80 (confidence 0.670). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **giftability**: 7.90 (confidence 0.670). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **insider_resonance**: 9.15 (confidence 0.700). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **ip_safety**: 8.80 (confidence 0.670). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **niche_fit**: 9.33 (confidence 0.700). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **visual_potential**: 8.95 (confidence 0.700). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.

#### Semiconductor — lot / tool / metrology
`semi_wafer_lot_tool_metrology` · ID `e68f66b6-854e-4950-a1b5-798915367b1f`

**Интерпретация:** Исторический: снят после owner review; не возвращать автоматически
**Статус БД:** scored · **балл:** 88.72 · **confidence:** 69.17 · **coverage:** 100.00
**Текст / хук:** WAFER • LOT • TOOL • METROLOGY
**Идея:** Semiconductor — lot / tool / metrology. Core hook: WAFER • LOT • TOOL • METROLOGY. Wafer processing, cleanroom equipment, lot control, inspection and metrology. Execution must stay original and descriptive; avoid employer, OEM, certification-body, association and proprietary-interface branding.
**Покупатель:** Semiconductor processing / wafer fab technicians
**Причина покупки:** Identity purchase for semiconductor processing / wafer fab technicians who recognize the real workflow/systems language.
**Отличие:** Insider technical system map direction intended to avoid generic profession-title, retro-badge, skull, flag, coffee and parody templates.
**Визуальное направление:** Fab-floor identity grid connecting material, equipment and measurement without manufacturer branding.
**retired_reason:** failed purchase-trigger quality bar after owner review
**Создано / обновлено:** 2026-09-23 09:48:50.541446+00 / 2026-09-23 23:40:31.847823+00

Компоненты оценки:
- **buyer_desire**: 8.54 (confidence 0.680). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **clarity_at_glance**: 8.20 (confidence 0.680). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **distinctiveness**: 9.10 (confidence 0.680). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **giftability**: 7.60 (confidence 0.680). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **insider_resonance**: 9.15 (confidence 0.710). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **ip_safety**: 8.80 (confidence 0.680). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **niche_fit**: 9.33 (confidence 0.710). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **visual_potential**: 9.65 (confidence 0.710). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.

#### Fab tech — bathroom logistics
`v4_semi_bathroom_mission` · ID `09fa8183-d806-4c81-be5b-cfb07450cf7d`

**Интерпретация:** Исследовательский кандидат; одобрение владельца не зафиксировано
**Статус БД:** scored · **балл:** 91.06 · **confidence:** 70.32 · **coverage:** 100.00
**Текст / хук:** BUILDING THE FUTURE. SCHEDULING BATHROOM BREAKS.
**Идея:** Contrast futuristic manufacturing with primitive human logistics.
**Покупатель:** Semiconductor processing / fab technicians
**Причина покупки:** Strong contrast joke, understandable and giftable.
**Отличие:** Human reality versus high technology, not a process list.
**Визуальное направление:** Futuristic wafer-fab skyline next to a hilariously formal bathroom mission plan.
**Создано / обновлено:** 2026-09-23 19:58:09.189566+00 / 2026-09-24 05:05:38.621539+00

Компоненты оценки:
- **buyer_desire**: 9.10 (confidence 0.700). purchase_trigger_v2 preliminary score; gate passed; trigger=contrast_humor Дата: 2026-09-23 19:59:53.152527+00.
- **clarity_at_glance**: 9.30 (confidence 0.760). purchase_trigger_v2 preliminary score; gate passed; trigger=contrast_humor Дата: 2026-09-23 19:59:53.152527+00.
- **distinctiveness**: 9.00 (confidence 0.700). purchase_trigger_v2 preliminary score; gate passed; trigger=contrast_humor Дата: 2026-09-23 19:59:53.152527+00.
- **giftability**: 8.90 (confidence 0.670). purchase_trigger_v2 preliminary score; gate passed; trigger=contrast_humor Дата: 2026-09-23 19:59:53.152527+00.
- **insider_resonance**: 9.30 (confidence 0.720). purchase_trigger_v2 preliminary score; gate passed; trigger=contrast_humor Дата: 2026-09-23 19:59:53.152527+00.
- **ip_safety**: 8.90 (confidence 0.600). purchase_trigger_v2 preliminary score; gate passed; trigger=contrast_humor Дата: 2026-09-23 19:59:53.152527+00.
- **niche_fit**: 9.20 (confidence 0.720). purchase_trigger_v2 preliminary score; gate passed; trigger=contrast_humor Дата: 2026-09-23 19:59:53.152527+00.
- **visual_potential**: 9.10 (confidence 0.720). purchase_trigger_v2 preliminary score; gate passed; trigger=contrast_humor Дата: 2026-09-23 19:59:53.152527+00.

#### Fab tech — twelve-hour bunny suit
`v4_semi_bunny_shift` · ID `317be766-f5c4-49d5-b3b8-33ad33dec5eb`

**Интерпретация:** Исследовательский кандидат; одобрение владельца не зафиксировано
**Статус БД:** scored · **балл:** 88.68 · **confidence:** 70.32 · **coverage:** 100.00
**Текст / хук:** 12 HOURS IN A BUNNY SUIT. ASK ME ABOUT COMFORT.
**Идея:** Shift-life solidarity around long hours in cleanroom gear.
**Покупатель:** Semiconductor processing / fab technicians
**Причина покупки:** Self-deprecating shift humor and a strong coworker gift angle.
**Отличие:** The joke is physical experience, not technical terminology.
**Визуальное направление:** Exhausted cleanroom-suit character beside an absurd comfort-rating meter.
**Создано / обновлено:** 2026-09-23 19:58:09.189566+00 / 2026-09-24 05:05:38.621539+00

Компоненты оценки:
- **buyer_desire**: 8.90 (confidence 0.700). purchase_trigger_v2 preliminary score; gate passed; trigger=shift_humor Дата: 2026-09-23 19:59:53.152527+00.
- **clarity_at_glance**: 9.20 (confidence 0.760). purchase_trigger_v2 preliminary score; gate passed; trigger=shift_humor Дата: 2026-09-23 19:59:53.152527+00.
- **distinctiveness**: 8.50 (confidence 0.700). purchase_trigger_v2 preliminary score; gate passed; trigger=shift_humor Дата: 2026-09-23 19:59:53.152527+00.
- **giftability**: 8.90 (confidence 0.670). purchase_trigger_v2 preliminary score; gate passed; trigger=shift_humor Дата: 2026-09-23 19:59:53.152527+00.
- **insider_resonance**: 9.10 (confidence 0.720). purchase_trigger_v2 preliminary score; gate passed; trigger=shift_humor Дата: 2026-09-23 19:59:53.152527+00.
- **ip_safety**: 8.90 (confidence 0.600). purchase_trigger_v2 preliminary score; gate passed; trigger=shift_humor Дата: 2026-09-23 19:59:53.152527+00.
- **niche_fit**: 9.10 (confidence 0.720). purchase_trigger_v2 preliminary score; gate passed; trigger=shift_humor Дата: 2026-09-23 19:59:53.152527+00.
- **visual_potential**: 8.60 (confidence 0.720). purchase_trigger_v2 preliminary score; gate passed; trigger=shift_humor Дата: 2026-09-23 19:59:53.152527+00.

#### Fab tech — coffee versus gowning
`v4_semi_coffee` · ID `5879416f-0f5b-4190-9a4e-031be2442030`

**Интерпретация:** V4: редакционный финалист на выбор владельца, НЕ подтвержденное одобрение
**Статус БД:** shortlisted · **балл:** 93.19 · **confidence:** 70.32 · **coverage:** 100.00
**Текст / хук:** GOWN. UNGOWN. REGRET THE COFFEE. REPEAT.
**Идея:** Cleanroom life joke about regretting fluids because every bathroom trip means ungowning and regowning.
**Покупатель:** Semiconductor processing / fab technicians
**Причина покупки:** High-recognition cleanroom humor with broad wearability.
**Отличие:** The joke is human inconvenience, not wafer terminology.
**Визуальное направление:** Coffee cup caught in a loop diagram of gowning stages, stylized not procedural.
**Смысл для владельца (источник, EN):** Coffee eventually means a bathroom break. In a cleanroom, that can mean leaving the controlled area, ungowning, then repeating the gowning routine when you come back.
**Почему это шутка (источник, EN):** The joke is that a completely normal choice — drinking coffee — creates an annoyingly elaborate chain of work. Fab workers recognize the daily calculation immediately: is the coffee worth having to do all that again?
**Создано / обновлено:** 2026-09-23 19:58:09.189566+00 / 2026-09-24 22:40:42.70901+00

Компоненты оценки:
- **buyer_desire**: 9.50 (confidence 0.700). purchase_trigger_v2 preliminary score; gate passed; trigger=cleanroom_life_humor Дата: 2026-09-23 19:59:53.152527+00.
- **clarity_at_glance**: 9.40 (confidence 0.760). purchase_trigger_v2 preliminary score; gate passed; trigger=cleanroom_life_humor Дата: 2026-09-23 19:59:53.152527+00.
- **distinctiveness**: 9.10 (confidence 0.700). purchase_trigger_v2 preliminary score; gate passed; trigger=cleanroom_life_humor Дата: 2026-09-23 19:59:53.152527+00.
- **giftability**: 9.20 (confidence 0.670). purchase_trigger_v2 preliminary score; gate passed; trigger=cleanroom_life_humor Дата: 2026-09-23 19:59:53.152527+00.
- **insider_resonance**: 9.50 (confidence 0.720). purchase_trigger_v2 preliminary score; gate passed; trigger=cleanroom_life_humor Дата: 2026-09-23 19:59:53.152527+00.
- **ip_safety**: 8.90 (confidence 0.600). purchase_trigger_v2 preliminary score; gate passed; trigger=cleanroom_life_humor Дата: 2026-09-23 19:59:53.152527+00.
- **niche_fit**: 9.40 (confidence 0.720). purchase_trigger_v2 preliminary score; gate passed; trigger=cleanroom_life_humor Дата: 2026-09-23 19:59:53.152527+00.
- **visual_potential**: 9.10 (confidence 0.720). purchase_trigger_v2 preliminary score; gate passed; trigger=cleanroom_life_humor Дата: 2026-09-23 19:59:53.152527+00.

#### Fab tech — dust outranks me
`v4_semi_dust_authority` · ID `49a879c5-ffaa-4b03-9325-60ee05541e54`

**Интерпретация:** V4: редакционный финалист на выбор владельца, НЕ подтвержденное одобрение
**Статус БД:** shortlisted · **балл:** 90.51 · **confidence:** 70.32 · **coverage:** 100.00
**Текст / хук:** ONE SPECK OF DUST OUTRANKS ME.
**Идея:** Personify contamination rules as a tiny speck having more authority than the worker.
**Покупатель:** Semiconductor processing / fab technicians
**Причина покупки:** Visual humor and cleanroom identity with low jargon dependence.
**Отличие:** The premise is power/status inversion, not cleanroom terminology.
**Визуальное направление:** Tiny dust particle wearing a manager badge above a suited technician.
**Смысл для владельца (источник, EN):** The technician jokes that a microscopic speck of dust has more authority than they do because contamination rules dictate what everyone can touch, wear and do.
**Почему это шутка (источник, EN):** The absurdity is the power hierarchy: a nearly invisible particle “outranks” a human employee. It turns strict cleanroom discipline into a tiny manager character.
**Создано / обновлено:** 2026-09-23 19:58:09.189566+00 / 2026-09-24 22:40:42.70901+00

Компоненты оценки:
- **buyer_desire**: 8.90 (confidence 0.700). purchase_trigger_v2 preliminary score; gate passed; trigger=visual_absurdity Дата: 2026-09-23 19:59:53.152527+00.
- **clarity_at_glance**: 9.10 (confidence 0.760). purchase_trigger_v2 preliminary score; gate passed; trigger=visual_absurdity Дата: 2026-09-23 19:59:53.152527+00.
- **distinctiveness**: 9.20 (confidence 0.700). purchase_trigger_v2 preliminary score; gate passed; trigger=visual_absurdity Дата: 2026-09-23 19:59:53.152527+00.
- **giftability**: 8.80 (confidence 0.670). purchase_trigger_v2 preliminary score; gate passed; trigger=visual_absurdity Дата: 2026-09-23 19:59:53.152527+00.
- **insider_resonance**: 9.10 (confidence 0.720). purchase_trigger_v2 preliminary score; gate passed; trigger=visual_absurdity Дата: 2026-09-23 19:59:53.152527+00.
- **ip_safety**: 8.90 (confidence 0.600). purchase_trigger_v2 preliminary score; gate passed; trigger=visual_absurdity Дата: 2026-09-23 19:59:53.152527+00.
- **niche_fit**: 9.10 (confidence 0.720). purchase_trigger_v2 preliminary score; gate passed; trigger=visual_absurdity Дата: 2026-09-23 19:59:53.152527+00.
- **visual_potential**: 9.40 (confidence 0.720). purchase_trigger_v2 preliminary score; gate passed; trigger=visual_absurdity Дата: 2026-09-23 19:59:53.152527+00.

#### Fab tech — advanced tech, ordinary human
`v4_semi_future_human` · ID `bffa5bf9-c496-48a4-9b59-600095efe9f7`

**Интерпретация:** Исследовательский кандидат; одобрение владельца не зафиксировано
**Статус БД:** scored · **балл:** 87.03 · **confidence:** 70.32 · **coverage:** 100.00
**Текст / хук:** MOST ADVANCED MACHINES ON EARTH. STILL HUMAN INSIDE THE SUIT.
**Идея:** Pride and humor in working around incredible machines while still dealing with normal human limitations.
**Покупатель:** Semiconductor processing / fab technicians
**Причина покупки:** Pride + humility with a strong visual contrast.
**Отличие:** Not a list of fab tools; the contrast is the idea.
**Визуальное направление:** Massive futuristic tool silhouette with a small tired suited human foreground.
**Создано / обновлено:** 2026-09-23 19:58:09.189566+00 / 2026-09-24 05:05:38.621539+00

Компоненты оценки:
- **buyer_desire**: 8.50 (confidence 0.700). purchase_trigger_v2 preliminary score; gate passed; trigger=pride_contrast Дата: 2026-09-23 19:59:53.152527+00.
- **clarity_at_glance**: 8.80 (confidence 0.760). purchase_trigger_v2 preliminary score; gate passed; trigger=pride_contrast Дата: 2026-09-23 19:59:53.152527+00.
- **distinctiveness**: 8.60 (confidence 0.700). purchase_trigger_v2 preliminary score; gate passed; trigger=pride_contrast Дата: 2026-09-23 19:59:53.152527+00.
- **giftability**: 8.20 (confidence 0.670). purchase_trigger_v2 preliminary score; gate passed; trigger=pride_contrast Дата: 2026-09-23 19:59:53.152527+00.
- **insider_resonance**: 8.90 (confidence 0.720). purchase_trigger_v2 preliminary score; gate passed; trigger=pride_contrast Дата: 2026-09-23 19:59:53.152527+00.
- **ip_safety**: 8.90 (confidence 0.600). purchase_trigger_v2 preliminary score; gate passed; trigger=pride_contrast Дата: 2026-09-23 19:59:53.152527+00.
- **niche_fit**: 9.10 (confidence 0.720). purchase_trigger_v2 preliminary score; gate passed; trigger=pride_contrast Дата: 2026-09-23 19:59:53.152527+00.
- **visual_potential**: 9.20 (confidence 0.720). purchase_trigger_v2 preliminary score; gate passed; trigger=pride_contrast Дата: 2026-09-23 19:59:53.152527+00.

## 42. Stationary Engineer / Boiler Operator
Ключ: `stationary_engineer_boiler_operator` · ID: `a2a6c202-6947-484a-aa53-f078b3cb3835`

**Статус БД:** scored · **балл:** 78.25 · **confidence:** 66.05 · **coverage:** 100.00
**Аудитория:** Stationary engineers, boiler operators and central-plant operators
**Категория:** occupational_identity
**Исследовательская аргументация:** Compact but durable 24/7 plant-operations niche with high visual specificity: steam, pressure, temperature, water level, burners, chillers and control-room instrumentation. Sampled Etsy merch is unusually thin.
**Создано / обновлено:** 2026-09-23 09:34:00.70472+00 / 2026-09-23 09:34:30.438105+00

### Компоненты оценки ниши

- **channel_breadth**: 6.50 (confidence 0.500). Initial evidence-weighted Forge score from current BLS/O*NET data, sampled Etsy competition and practitioner-community signals. See niche_candidates.source_notes. This is prioritization research, not a sales forecast. Дата: 2026-09-23 09:34:30.438105+00.
- **competition_opportunity**: 9.00 (confidence 0.650). Initial evidence-weighted Forge score from current BLS/O*NET data, sampled Etsy competition and practitioner-community signals. See niche_candidates.source_notes. This is prioritization research, not a sales forecast. Дата: 2026-09-23 09:34:30.438105+00.
- **concept_depth**: 9.00 (confidence 0.700). Initial evidence-weighted Forge score from current BLS/O*NET data, sampled Etsy competition and practitioner-community signals. See niche_candidates.source_notes. This is prioritization research, not a sales forecast. Дата: 2026-09-23 09:34:30.438105+00.
- **demand_evidence**: 6.50 (confidence 0.750). Initial evidence-weighted Forge score from current BLS/O*NET data, sampled Etsy competition and practitioner-community signals. See niche_candidates.source_notes. This is prioritization research, not a sales forecast. Дата: 2026-09-23 09:34:30.438105+00.
- **founder_edge**: 2.00 (confidence 0.400). Initial evidence-weighted Forge score from current BLS/O*NET data, sampled Etsy competition and practitioner-community signals. See niche_candidates.source_notes. This is prioritization research, not a sales forecast. Дата: 2026-09-23 09:34:30.438105+00.
- **identity_intensity**: 8.00 (confidence 0.650). Initial evidence-weighted Forge score from current BLS/O*NET data, sampled Etsy competition and practitioner-community signals. See niche_candidates.source_notes. This is prioritization research, not a sales forecast. Дата: 2026-09-23 09:34:30.438105+00.
- **legal_safety**: 9.00 (confidence 0.700). Initial evidence-weighted Forge score from current BLS/O*NET data, sampled Etsy competition and practitioner-community signals. See niche_candidates.source_notes. This is prioritization research, not a sales forecast. Дата: 2026-09-23 09:34:30.438105+00.
- **purchase_motivation**: 7.50 (confidence 0.600). Initial evidence-weighted Forge score from current BLS/O*NET data, sampled Etsy competition and practitioner-community signals. See niche_candidates.source_notes. This is prioritization research, not a sales forecast. Дата: 2026-09-23 09:34:30.438105+00.
- **repeatability**: 7.50 (confidence 0.550). Initial evidence-weighted Forge score from current BLS/O*NET data, sampled Etsy competition and practitioner-community signals. See niche_candidates.source_notes. This is prioritization research, not a sales forecast. Дата: 2026-09-23 09:34:30.438105+00.
- **visual_language**: 9.50 (confidence 0.750). Initial evidence-weighted Forge score from current BLS/O*NET data, sampled Etsy competition and practitioner-community signals. See niche_candidates.source_notes. This is prioritization research, not a sales forecast. Дата: 2026-09-23 09:34:30.438105+00.

### Концепции (3)

#### Boiler Operator — water / air / fuel / steam
`boiler_water_air_fuel_steam_control` · ID `15541450-57e8-4177-b54e-c227b9fd05c1`

**Интерпретация:** Исследовательский кандидат; одобрение владельца не зафиксировано
**Статус БД:** scored · **балл:** 88.36 · **confidence:** 68.94 · **coverage:** 100.00
**Текст / хук:** WATER • AIR • FUEL → STEAM
**Идея:** BOILER OPERATOR technical system concept structured as WATER • AIR • FUEL → STEAM, with CONTROL as the governing layer. Based on real operator duties of monitoring levels, valves, fuel and safe operating limits.
**Покупатель:** Boiler operators and stationary engineers
**Причина покупки:** Recognizable operating-system identity with strong mechanical visual language.
**Отличие:** Process logic instead of steampunk decoration or generic boiler-room imagery.
**Визуальное направление:** Original boiler cross-section / flow arrows / pressure-temperature gauge motifs
**Создано / обновлено:** 2026-09-23 09:36:02.928333+00 / 2026-09-23 10:09:42.905504+00

Компоненты оценки:
- **buyer_desire**: 8.00 (confidence 0.620). Initial Forge concept score using current occupational terminology, sampled marketplace patterns and technical distinctiveness. No visual has been generated; exact phrases still require IP/common-law screening before promotion. Дата: 2026-09-23 09:36:38.256823+00.
- **clarity_at_glance**: 8.00 (confidence 0.620). Initial Forge concept score using current occupational terminology, sampled marketplace patterns and technical distinctiveness. No visual has been generated; exact phrases still require IP/common-law screening before promotion. Дата: 2026-09-23 09:36:38.256823+00.
- **distinctiveness**: 9.20 (confidence 0.700). Initial Forge concept score using current occupational terminology, sampled marketplace patterns and technical distinctiveness. No visual has been generated; exact phrases still require IP/common-law screening before promotion. Дата: 2026-09-23 09:36:38.256823+00.
- **giftability**: 7.50 (confidence 0.580). Initial Forge concept score using current occupational terminology, sampled marketplace patterns and technical distinctiveness. No visual has been generated; exact phrases still require IP/common-law screening before promotion. Дата: 2026-09-23 09:36:38.256823+00.
- **insider_resonance**: 9.50 (confidence 0.760). Initial Forge concept score using current occupational terminology, sampled marketplace patterns and technical distinctiveness. No visual has been generated; exact phrases still require IP/common-law screening before promotion. Дата: 2026-09-23 09:36:38.256823+00.
- **ip_safety**: 9.50 (confidence 0.720). Initial Forge concept score using current occupational terminology, sampled marketplace patterns and technical distinctiveness. No visual has been generated; exact phrases still require IP/common-law screening before promotion. Дата: 2026-09-23 09:36:38.256823+00.
- **niche_fit**: 9.50 (confidence 0.780). Initial Forge concept score using current occupational terminology, sampled marketplace patterns and technical distinctiveness. No visual has been generated; exact phrases still require IP/common-law screening before promotion. Дата: 2026-09-23 09:36:38.256823+00.
- **visual_potential**: 9.50 (confidence 0.740). Initial Forge concept score using current occupational terminology, sampled marketplace patterns and technical distinctiveness. No visual has been generated; exact phrases still require IP/common-law screening before promotion. Дата: 2026-09-23 09:36:38.256823+00.

#### Stationary Engineer — central plant
`stationary_central_plant_steam_chilled_water_power` · ID `55bcd749-070d-4cf8-b0a1-795a8d1585d5`

**Интерпретация:** Исследовательский кандидат; одобрение владельца не зафиксировано
**Статус БД:** scored · **балл:** 87.69 · **confidence:** 68.42 · **coverage:** 100.00
**Текст / хук:** STEAM • CHILLED WATER • POWER
**Идея:** STATIONARY ENGINEER / CENTRAL PLANT identity using STEAM • CHILLED WATER • POWER and an original simplified plant-flow schematic connecting boiler, chiller/pump and generator/utility systems.
**Покупатель:** Stationary engineers and central-plant operators
**Причина покупки:** Captures whole-plant responsibility rather than a single boiler joke.
**Отличие:** Central-plant systems language is rarely represented in sampled merch.
**Визуальное направление:** Industrial flow diagram with boiler/chiller/pump/generator blocks and gauges
**Создано / обновлено:** 2026-09-23 09:36:02.928333+00 / 2026-09-23 10:09:42.905504+00

Компоненты оценки:
- **buyer_desire**: 8.20 (confidence 0.640). Initial Forge concept score using current occupational terminology, sampled marketplace patterns and technical distinctiveness. No visual has been generated; exact phrases still require IP/common-law screening before promotion. Дата: 2026-09-23 09:36:38.256823+00.
- **clarity_at_glance**: 8.50 (confidence 0.660). Initial Forge concept score using current occupational terminology, sampled marketplace patterns and technical distinctiveness. No visual has been generated; exact phrases still require IP/common-law screening before promotion. Дата: 2026-09-23 09:36:38.256823+00.
- **distinctiveness**: 9.00 (confidence 0.680). Initial Forge concept score using current occupational terminology, sampled marketplace patterns and technical distinctiveness. No visual has been generated; exact phrases still require IP/common-law screening before promotion. Дата: 2026-09-23 09:36:38.256823+00.
- **giftability**: 7.50 (confidence 0.580). Initial Forge concept score using current occupational terminology, sampled marketplace patterns and technical distinctiveness. No visual has been generated; exact phrases still require IP/common-law screening before promotion. Дата: 2026-09-23 09:36:38.256823+00.
- **insider_resonance**: 9.00 (confidence 0.720). Initial Forge concept score using current occupational terminology, sampled marketplace patterns and technical distinctiveness. No visual has been generated; exact phrases still require IP/common-law screening before promotion. Дата: 2026-09-23 09:36:38.256823+00.
- **ip_safety**: 9.00 (confidence 0.680). Initial Forge concept score using current occupational terminology, sampled marketplace patterns and technical distinctiveness. No visual has been generated; exact phrases still require IP/common-law screening before promotion. Дата: 2026-09-23 09:36:38.256823+00.
- **niche_fit**: 9.50 (confidence 0.780). Initial Forge concept score using current occupational terminology, sampled marketplace patterns and technical distinctiveness. No visual has been generated; exact phrases still require IP/common-law screening before promotion. Дата: 2026-09-23 09:36:38.256823+00.
- **visual_potential**: 9.50 (confidence 0.740). Initial Forge concept score using current occupational terminology, sampled marketplace patterns and technical distinctiveness. No visual has been generated; exact phrases still require IP/common-law screening before promotion. Дата: 2026-09-23 09:36:38.256823+00.

#### Stationary Engineer — read / adjust / verify / log
`stationary_read_adjust_verify_log` · ID `f3b1bc92-c382-41c0-9ee7-787c95c1e91b`

**Интерпретация:** Исследовательский кандидат; одобрение владельца не зафиксировано
**Статус БД:** scored · **балл:** 83.35 · **confidence:** 64.08 · **coverage:** 100.00
**Текст / хук:** READ • ADJUST • VERIFY • LOG
**Идея:** STATIONARY ENGINEER operating loop: READ • ADJUST • VERIFY • LOG, referencing the real work of reading gauges/meters, regulating equipment, checking safety devices and keeping operating records.
**Покупатель:** Stationary engineers and boiler operators
**Причина покупки:** Understated insider workflow suitable for workwear-style merch.
**Отличие:** Operational discipline rather than generic wrench graphics.
**Визуальное направление:** Gauge cluster plus concise four-step loop; industrial work-order aesthetic
**Создано / обновлено:** 2026-09-23 09:36:02.928333+00 / 2026-09-23 10:09:42.905504+00

Компоненты оценки:
- **buyer_desire**: 7.50 (confidence 0.580). Initial Forge concept score using current occupational terminology, sampled marketplace patterns and technical distinctiveness. No visual has been generated; exact phrases still require IP/common-law screening before promotion. Дата: 2026-09-23 09:36:38.256823+00.
- **clarity_at_glance**: 8.50 (confidence 0.660). Initial Forge concept score using current occupational terminology, sampled marketplace patterns and technical distinctiveness. No visual has been generated; exact phrases still require IP/common-law screening before promotion. Дата: 2026-09-23 09:36:38.256823+00.
- **distinctiveness**: 8.50 (confidence 0.640). Initial Forge concept score using current occupational terminology, sampled marketplace patterns and technical distinctiveness. No visual has been generated; exact phrases still require IP/common-law screening before promotion. Дата: 2026-09-23 09:36:38.256823+00.
- **giftability**: 7.00 (confidence 0.540). Initial Forge concept score using current occupational terminology, sampled marketplace patterns and technical distinctiveness. No visual has been generated; exact phrases still require IP/common-law screening before promotion. Дата: 2026-09-23 09:36:38.256823+00.
- **insider_resonance**: 9.00 (confidence 0.700). Initial Forge concept score using current occupational terminology, sampled marketplace patterns and technical distinctiveness. No visual has been generated; exact phrases still require IP/common-law screening before promotion. Дата: 2026-09-23 09:36:38.256823+00.
- **ip_safety**: 9.50 (confidence 0.720). Initial Forge concept score using current occupational terminology, sampled marketplace patterns and technical distinctiveness. No visual has been generated; exact phrases still require IP/common-law screening before promotion. Дата: 2026-09-23 09:36:38.256823+00.
- **niche_fit**: 9.00 (confidence 0.720). Initial Forge concept score using current occupational terminology, sampled marketplace patterns and technical distinctiveness. No visual has been generated; exact phrases still require IP/common-law screening before promotion. Дата: 2026-09-23 09:36:38.256823+00.
- **visual_potential**: 8.50 (confidence 0.640). Initial Forge concept score using current occupational terminology, sampled marketplace patterns and technical distinctiveness. No visual has been generated; exact phrases still require IP/common-law screening before promotion. Дата: 2026-09-23 09:36:38.256823+00.

## 43. Sterile Processing
Ключ: `sterile_processing` · ID: `38220d7b-2525-4b98-9091-5b86760f76b5`

**Статус БД:** shortlisted · **балл:** 82.75 · **confidence:** 80.70 · **coverage:** 100.00
**Аудитория:** Sterile processing technicians / central service staff
**Категория:** occupational_identity
**Исследовательская аргументация:** Legacy Town Label occupational niche carried forward for re-evaluation under the new niche-first scoring engine. Existing artwork quality does not determine niche status.
**Создано / обновлено:** 2026-09-23 06:11:01.997287+00 / 2026-09-23 10:03:30.159451+00

### Компоненты оценки ниши

- **channel_breadth**: 8.00 (confidence 0.660). Legacy Forge/Town Label niche rescored under the unified Forge rubric using current 2025-35 BLS data plus the 2026-09-21/22 marketplace and IP research already stored in merch.research_notes. Existing visual rejection does not count as niche rejection. Дата: 2026-09-23 09:44:55.053118+00.
- **competition_opportunity**: 6.50 (confidence 0.860). Legacy Forge/Town Label niche rescored under the unified Forge rubric using current 2025-35 BLS data plus the 2026-09-21/22 marketplace and IP research already stored in merch.research_notes. Existing visual rejection does not count as niche rejection. Дата: 2026-09-23 09:44:55.053118+00.
- **concept_depth**: 9.50 (confidence 0.820). Legacy Forge/Town Label niche rescored under the unified Forge rubric using current 2025-35 BLS data plus the 2026-09-21/22 marketplace and IP research already stored in merch.research_notes. Existing visual rejection does not count as niche rejection. Дата: 2026-09-23 09:44:55.053118+00.
- **demand_evidence**: 8.50 (confidence 0.880). Legacy Forge/Town Label niche rescored under the unified Forge rubric using current 2025-35 BLS data plus the 2026-09-21/22 marketplace and IP research already stored in merch.research_notes. Existing visual rejection does not count as niche rejection. Дата: 2026-09-23 09:44:55.053118+00.
- **founder_edge**: 2.00 (confidence 0.400). Legacy Forge/Town Label niche rescored under the unified Forge rubric using current 2025-35 BLS data plus the 2026-09-21/22 marketplace and IP research already stored in merch.research_notes. Existing visual rejection does not count as niche rejection. Дата: 2026-09-23 09:44:55.053118+00.
- **identity_intensity**: 9.00 (confidence 0.820). Legacy Forge/Town Label niche rescored under the unified Forge rubric using current 2025-35 BLS data plus the 2026-09-21/22 marketplace and IP research already stored in merch.research_notes. Existing visual rejection does not count as niche rejection. Дата: 2026-09-23 09:44:55.053118+00.
- **legal_safety**: 7.50 (confidence 0.720). Legacy Forge/Town Label niche rescored under the unified Forge rubric using current 2025-35 BLS data plus the 2026-09-21/22 marketplace and IP research already stored in merch.research_notes. Existing visual rejection does not count as niche rejection. Дата: 2026-09-23 09:44:55.053118+00.
- **purchase_motivation**: 8.50 (confidence 0.780). Legacy Forge/Town Label niche rescored under the unified Forge rubric using current 2025-35 BLS data plus the 2026-09-21/22 marketplace and IP research already stored in merch.research_notes. Existing visual rejection does not count as niche rejection. Дата: 2026-09-23 09:44:55.053118+00.
- **repeatability**: 9.00 (confidence 0.740). Legacy Forge/Town Label niche rescored under the unified Forge rubric using current 2025-35 BLS data plus the 2026-09-21/22 marketplace and IP research already stored in merch.research_notes. Existing visual rejection does not count as niche rejection. Дата: 2026-09-23 09:44:55.053118+00.
- **visual_language**: 9.00 (confidence 0.800). Legacy Forge/Town Label niche rescored under the unified Forge rubric using current 2025-35 BLS data plus the 2026-09-21/22 marketplace and IP research already stored in merch.research_notes. Existing visual rejection does not count as niche rejection. Дата: 2026-09-23 09:44:55.053118+00.

### Концепции (12)

#### SPD — clean / complete / functional / ready
`spd_clean_complete_functional_ready` · ID `0c11791c-bbe0-4d16-86ce-392a6801d456`

**Интерпретация:** Исследовательский кандидат; одобрение владельца не зафиксировано
**Статус БД:** scored · **балл:** 86.54 · **confidence:** 67.17 · **coverage:** 100.00
**Текст / хук:** CLEAN • COMPLETE • FUNCTIONAL • READY
**Идея:** SPD — clean / complete / functional / ready. Core hook: CLEAN • COMPLETE • FUNCTIONAL • READY. Sterilization, tray assembly, inspection, tracking and quality-control identity. Execution must stay original and descriptive; avoid employer, OEM, certification-body, association and proprietary-interface branding.
**Покупатель:** Sterile processing / central service technicians
**Причина покупки:** Identity purchase for sterile processing / central service technicians who recognize the real workflow/systems language.
**Отличие:** Insider technical terminology direction intended to avoid generic profession-title, retro-badge, skull, flag, coffee and parody templates.
**Визуальное направление:** Four-state quality standard rendered as an instrument-tray status panel; identity art, not an instructional checklist.
**Создано / обновлено:** 2026-09-23 09:48:50.541446+00 / 2026-09-23 09:55:40.114238+00

Компоненты оценки:
- **buyer_desire**: 8.02 (confidence 0.660). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **clarity_at_glance**: 9.23 (confidence 0.660). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **distinctiveness**: 8.40 (confidence 0.660). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **giftability**: 8.13 (confidence 0.660). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **insider_resonance**: 9.45 (confidence 0.690). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **ip_safety**: 8.80 (confidence 0.660). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **niche_fit**: 9.50 (confidence 0.690). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **visual_potential**: 8.45 (confidence 0.690). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.

#### SPD — count / inspect / verify
`spd_count_inspect_verify_release` · ID `011701ac-32ac-4819-89d5-69c90d269bfd`

**Интерпретация:** Исторический: снят после owner review; не возвращать автоматически
**Статус БД:** scored · **балл:** 88.92 · **confidence:** 69.17 · **coverage:** 100.00
**Текст / хук:** COUNT • INSPECT • VERIFY • RELEASE
**Идея:** SPD — count / inspect / verify. Core hook: COUNT • INSPECT • VERIFY • RELEASE. Sterilization, tray assembly, inspection, tracking and quality-control identity. Execution must stay original and descriptive; avoid employer, OEM, certification-body, association and proprietary-interface branding.
**Покупатель:** Sterile processing / central service technicians
**Причина покупки:** Identity purchase for sterile processing / central service technicians who recognize the real workflow/systems language.
**Отличие:** Insider technical diagnostic direction intended to avoid generic profession-title, retro-badge, skull, flag, coffee and parody templates.
**Визуальное направление:** Quality-control identity centered on completeness and inspection, using tray-grid geometry.
**retired_reason:** failed purchase-trigger quality bar after owner review
**Создано / обновлено:** 2026-09-23 09:48:50.541446+00 / 2026-09-23 23:40:31.847823+00

Компоненты оценки:
- **buyer_desire**: 8.72 (confidence 0.680). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **clarity_at_glance**: 8.57 (confidence 0.680). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **distinctiveness**: 9.00 (confidence 0.680). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **giftability**: 7.87 (confidence 0.680). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **insider_resonance**: 9.40 (confidence 0.710). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **ip_safety**: 8.70 (confidence 0.680). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **niche_fit**: 9.50 (confidence 0.710). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **visual_potential**: 8.90 (confidence 0.710). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.

#### SPD — department flow
`spd_decon_assembly_sterilize_storage` · ID `c38b0710-ac07-4129-8275-d6d44250c254`

**Интерпретация:** Исследовательский кандидат; одобрение владельца не зафиксировано
**Статус БД:** scored · **балл:** 87.32 · **confidence:** 68.17 · **coverage:** 100.00
**Текст / хук:** DECON → ASSEMBLY → STERILIZE → STORAGE
**Идея:** SPD — department flow. Core hook: DECON → ASSEMBLY → STERILIZE → STORAGE. Sterilization, tray assembly, inspection, tracking and quality-control identity. Execution must stay original and descriptive; avoid employer, OEM, certification-body, association and proprietary-interface branding.
**Покупатель:** Sterile processing / central service technicians
**Причина покупки:** Identity purchase for sterile processing / central service technicians who recognize the real workflow/systems language.
**Отличие:** Insider technical process direction intended to avoid generic profession-title, retro-badge, skull, flag, coffee and parody templates.
**Визуальное направление:** Department-flow graphic using clean original wayfinding geometry; no association marks, certification seals or hospital branding.
**Создано / обновлено:** 2026-09-23 09:48:50.541446+00 / 2026-09-23 09:55:40.114238+00

Компоненты оценки:
- **buyer_desire**: 8.42 (confidence 0.670). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **clarity_at_glance**: 8.77 (confidence 0.670). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **distinctiveness**: 8.70 (confidence 0.670). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **giftability**: 7.87 (confidence 0.670). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **insider_resonance**: 9.10 (confidence 0.700). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **ip_safety**: 8.80 (confidence 0.670). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **niche_fit**: 9.40 (confidence 0.700). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **visual_potential**: 8.90 (confidence 0.700). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.

#### SPD — inspect / assemble / package
`spd_inspect_assemble_package` · ID `14a8a32f-610e-4a75-95cf-e57905a74b2b`

**Интерпретация:** Исследовательский кандидат; одобрение владельца не зафиксировано
**Статус БД:** scored · **балл:** 85.83 · **confidence:** 67.17 · **coverage:** 100.00
**Текст / хук:** INSPECT • ASSEMBLE • PACKAGE
**Идея:** SPD — inspect / assemble / package. Core hook: INSPECT • ASSEMBLE • PACKAGE. Sterilization, tray assembly, inspection, tracking and quality-control identity. Execution must stay original and descriptive; avoid employer, OEM, certification-body, association and proprietary-interface branding.
**Покупатель:** Sterile processing / central service technicians
**Причина покупки:** Identity purchase for sterile processing / central service technicians who recognize the real workflow/systems language.
**Отличие:** Insider technical workflow direction intended to avoid generic profession-title, retro-badge, skull, flag, coffee and parody templates.
**Визуальное направление:** Instrument-tray quality workflow with generic tray/instrument silhouettes and check points.
**Создано / обновлено:** 2026-09-23 09:48:50.541446+00 / 2026-09-23 09:55:40.114238+00

Компоненты оценки:
- **buyer_desire**: 8.32 (confidence 0.660). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **clarity_at_glance**: 9.17 (confidence 0.660). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **distinctiveness**: 8.40 (confidence 0.660). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **giftability**: 8.07 (confidence 0.660). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **insider_resonance**: 8.80 (confidence 0.690). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **ip_safety**: 9.00 (confidence 0.660). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **niche_fit**: 9.30 (confidence 0.690). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **visual_potential**: 8.40 (confidence 0.690). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.

#### SPD — instrument tracking cycle
`spd_instrument_tracking_cycle` · ID `d636e632-7cc3-4cce-8794-486b93c28776`

**Интерпретация:** Исследовательский кандидат; одобрение владельца не зафиксировано
**Статус БД:** scored · **балл:** 87.32 · **confidence:** 68.17 · **coverage:** 100.00
**Текст / хук:** RECEIVE → DECON → PREP → STERILIZE → ISSUE
**Идея:** SPD — instrument tracking cycle. Core hook: RECEIVE → DECON → PREP → STERILIZE → ISSUE. Sterilization, tray assembly, inspection, tracking and quality-control identity. Execution must stay original and descriptive; avoid employer, OEM, certification-body, association and proprietary-interface branding.
**Покупатель:** Sterile processing / central service technicians
**Причина покупки:** Identity purchase for sterile processing / central service technicians who recognize the real workflow/systems language.
**Отличие:** Insider technical process direction intended to avoid generic profession-title, retro-badge, skull, flag, coffee and parody templates.
**Визуальное направление:** Closed-loop instrument journey with tracking-tag motifs; generic and original, not a vendor tracking UI.
**Создано / обновлено:** 2026-09-23 09:48:50.541446+00 / 2026-09-23 09:55:40.114238+00

Компоненты оценки:
- **buyer_desire**: 8.42 (confidence 0.670). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **clarity_at_glance**: 8.77 (confidence 0.670). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **distinctiveness**: 8.70 (confidence 0.670). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **giftability**: 7.87 (confidence 0.670). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **insider_resonance**: 9.10 (confidence 0.700). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **ip_safety**: 8.80 (confidence 0.670). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **niche_fit**: 9.40 (confidence 0.700). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **visual_potential**: 8.90 (confidence 0.700). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.

#### SPD — load lifecycle
`spd_load_monitor_release_record` · ID `d9c7d0f5-d89a-41fd-bc1e-ce4debde25e1`

**Интерпретация:** Исследовательский кандидат; одобрение владельца не зафиксировано
**Статус БД:** scored · **балл:** 85.20 · **confidence:** 67.17 · **coverage:** 100.00
**Текст / хук:** LOAD • MONITOR • RELEASE • RECORD
**Идея:** SPD — load lifecycle. Core hook: LOAD • MONITOR • RELEASE • RECORD. Sterilization, tray assembly, inspection, tracking and quality-control identity. Execution must stay original and descriptive; avoid employer, OEM, certification-body, association and proprietary-interface branding.
**Покупатель:** Sterile processing / central service technicians
**Причина покупки:** Identity purchase for sterile processing / central service technicians who recognize the real workflow/systems language.
**Отличие:** Insider technical workflow direction intended to avoid generic profession-title, retro-badge, skull, flag, coffee and parody templates.
**Визуальное направление:** Sterilizer-load lifecycle as a restrained technical process diagram without procedural parameter values.
**Создано / обновлено:** 2026-09-23 09:48:50.541446+00 / 2026-09-23 09:55:40.114238+00

Компоненты оценки:
- **buyer_desire**: 8.22 (confidence 0.660). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **clarity_at_glance**: 9.13 (confidence 0.660). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **distinctiveness**: 8.30 (confidence 0.660). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **giftability**: 8.03 (confidence 0.660). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **insider_resonance**: 8.75 (confidence 0.690). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **ip_safety**: 9.00 (confidence 0.660). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **niche_fit**: 9.30 (confidence 0.690). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **visual_potential**: 8.35 (confidence 0.690). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.

#### Sterile Processing — one-way workflow
`sterile_processing_one_way_workflow` · ID `98f86f06-fd0d-4094-b74b-b8dd7f49170d`

**Интерпретация:** Исторический: снят после owner review; не возвращать автоматически
**Статус БД:** scored · **балл:** 89.80 · **confidence:** 74.17 · **coverage:** 100.00
**Текст / хук:** SOILED → CLEAN → STERILE
**Идея:** Sterile Processing one-way workflow design: strong STERILE PROCESSING identity plus a simple one-direction SOILED -> CLEAN -> STERILE progression. Visual language should feel like original industrial/departmental wayfinding—not an educational poster, copied hospital sign, certification badge, manufacturer UI, or generic nurse graphic.
**Покупатель:** Sterile processing technicians / central service staff
**Визуальное направление:** clean technical / instrument-tray / workflow; insider-recognizable; not generic nurse imagery
**retired_reason:** failed purchase-trigger quality bar after owner review
**Создано / обновлено:** 2026-09-23 06:11:42.741293+00 / 2026-09-23 23:40:31.847823+00

Компоненты оценки:
- **buyer_desire**: 8.64 (confidence 0.742). Unified Forge concept-depth score. Profile captures the concept form (technical map, diagnostic, system map, workflow, process or terminology); a small stored concept bias and bounded niche-quality adjustment prevent identical form scores across materially different niches. No visual was generated. Federal/common-law phrase review remains a separate gate. Дата: 2026-09-23 09:51:32.257179+00.
- **clarity_at_glance**: 8.50 (confidence 0.734). Unified Forge concept-depth score. Profile captures the concept form (technical map, diagnostic, system map, workflow, process or terminology); a small stored concept bias and bounded niche-quality adjustment prevent identical form scores across materially different niches. No visual was generated. Federal/common-law phrase review remains a separate gate. Дата: 2026-09-23 09:51:32.257179+00.
- **distinctiveness**: 9.10 (confidence 0.749). Unified Forge concept-depth score. Profile captures the concept form (technical map, diagnostic, system map, workflow, process or terminology); a small stored concept bias and bounded niche-quality adjustment prevent identical form scores across materially different niches. No visual was generated. Federal/common-law phrase review remains a separate gate. Дата: 2026-09-23 09:51:32.257179+00.
- **giftability**: 8.04 (confidence 0.704). Unified Forge concept-depth score. Profile captures the concept form (technical map, diagnostic, system map, workflow, process or terminology); a small stored concept bias and bounded niche-quality adjustment prevent identical form scores across materially different niches. No visual was generated. Federal/common-law phrase review remains a separate gate. Дата: 2026-09-23 09:51:32.257179+00.
- **insider_resonance**: 9.20 (confidence 0.764). Unified Forge concept-depth score. Profile captures the concept form (technical map, diagnostic, system map, workflow, process or terminology); a small stored concept bias and bounded niche-quality adjustment prevent identical form scores across materially different niches. No visual was generated. Federal/common-law phrase review remains a separate gate. Дата: 2026-09-23 09:51:32.257179+00.
- **ip_safety**: 9.00 (confidence 0.550). Unified Forge concept-depth score. Profile captures the concept form (technical map, diagnostic, system map, workflow, process or terminology); a small stored concept bias and bounded niche-quality adjustment prevent identical form scores across materially different niches. No visual was generated. Federal/common-law phrase review remains a separate gate. Дата: 2026-09-23 09:51:32.257179+00.
- **niche_fit**: 9.74 (confidence 0.779). Unified Forge concept-depth score. Profile captures the concept form (technical map, diagnostic, system map, workflow, process or terminology); a small stored concept bias and bounded niche-quality adjustment prevent identical form scores across materially different niches. No visual was generated. Federal/common-law phrase review remains a separate gate. Дата: 2026-09-23 09:51:32.257179+00.
- **visual_potential**: 9.50 (confidence 0.779). Unified Forge concept-depth score. Profile captures the concept form (technical map, diagnostic, system map, workflow, process or terminology); a small stored concept bias and bounded niche-quality adjustment prevent identical form scores across materially different niches. No visual was generated. Federal/common-law phrase review remains a separate gate. Дата: 2026-09-23 09:51:32.257179+00.

#### SPD — almost clean is dirty
`v4_spd_almost_clean` · ID `533f2448-d9b2-48b6-85a3-30cc5310302d`

**Интерпретация:** Исследовательский кандидат; одобрение владельца не зафиксировано
**Статус БД:** scored · **балл:** 83.47 · **confidence:** 70.32 · **coverage:** 100.00
**Текст / хук:** ALMOST CLEAN = DIRTY.
**Идея:** Turn the profession's uncompromising safety standard into an identity statement.
**Покупатель:** Sterile processing technicians
**Причина покупки:** Pride/status: the wearer signals the boundary they are paid to enforce.
**Отличие:** Short human standard, not a workflow list.
**Визуальное направление:** Bold binary stamp-style graphic; generic tray silhouette.
**Создано / обновлено:** 2026-09-23 19:58:09.189566+00 / 2026-09-24 05:05:38.621539+00

Компоненты оценки:
- **buyer_desire**: 8.00 (confidence 0.700). purchase_trigger_v2 preliminary score; gate passed; trigger=professional_pride Дата: 2026-09-23 19:59:53.152527+00.
- **clarity_at_glance**: 8.80 (confidence 0.760). purchase_trigger_v2 preliminary score; gate passed; trigger=professional_pride Дата: 2026-09-23 19:59:53.152527+00.
- **distinctiveness**: 7.90 (confidence 0.700). purchase_trigger_v2 preliminary score; gate passed; trigger=professional_pride Дата: 2026-09-23 19:59:53.152527+00.
- **giftability**: 8.00 (confidence 0.670). purchase_trigger_v2 preliminary score; gate passed; trigger=professional_pride Дата: 2026-09-23 19:59:53.152527+00.
- **insider_resonance**: 8.90 (confidence 0.720). purchase_trigger_v2 preliminary score; gate passed; trigger=professional_pride Дата: 2026-09-23 19:59:53.152527+00.
- **ip_safety**: 8.90 (confidence 0.600). purchase_trigger_v2 preliminary score; gate passed; trigger=professional_pride Дата: 2026-09-23 19:59:53.152527+00.
- **niche_fit**: 9.40 (confidence 0.720). purchase_trigger_v2 preliminary score; gate passed; trigger=professional_pride Дата: 2026-09-23 19:59:53.152527+00.
- **visual_potential**: 8.40 (confidence 0.720). purchase_trigger_v2 preliminary score; gate passed; trigger=professional_pride Дата: 2026-09-23 19:59:53.152527+00.

#### SPD — case cart killed my plans
`v4_spd_case_cart_plans` · ID `104e0c81-f426-48fe-b38c-c3afc84965d3`

**Интерпретация:** Исследовательский кандидат; одобрение владельца не зафиксировано
**Статус БД:** scored · **балл:** 88.68 · **confidence:** 70.32 · **coverage:** 100.00
**Текст / хук:** I HAD PLANS. THEN THE CASE CART ARRIVED.
**Идея:** Shift-life humor around the late case cart that destroys the end-of-day plan.
**Покупатель:** Sterile processing technicians
**Причина покупки:** Relatable work-life humor with a clear gifting occasion for coworkers.
**Отличие:** Situation-driven and understandable even without technical vocabulary.
**Визуальное направление:** Clock near shift end plus ominous rolling cart entering frame.
**Создано / обновлено:** 2026-09-23 19:58:09.189566+00 / 2026-09-24 05:05:38.621539+00

Компоненты оценки:
- **buyer_desire**: 8.90 (confidence 0.700). purchase_trigger_v2 preliminary score; gate passed; trigger=shift_humor Дата: 2026-09-23 19:59:53.152527+00.
- **clarity_at_glance**: 9.20 (confidence 0.760). purchase_trigger_v2 preliminary score; gate passed; trigger=shift_humor Дата: 2026-09-23 19:59:53.152527+00.
- **distinctiveness**: 8.50 (confidence 0.700). purchase_trigger_v2 preliminary score; gate passed; trigger=shift_humor Дата: 2026-09-23 19:59:53.152527+00.
- **giftability**: 8.90 (confidence 0.670). purchase_trigger_v2 preliminary score; gate passed; trigger=shift_humor Дата: 2026-09-23 19:59:53.152527+00.
- **insider_resonance**: 9.10 (confidence 0.720). purchase_trigger_v2 preliminary score; gate passed; trigger=shift_humor Дата: 2026-09-23 19:59:53.152527+00.
- **ip_safety**: 8.90 (confidence 0.600). purchase_trigger_v2 preliminary score; gate passed; trigger=shift_humor Дата: 2026-09-23 19:59:53.152527+00.
- **niche_fit**: 9.10 (confidence 0.720). purchase_trigger_v2 preliminary score; gate passed; trigger=shift_humor Дата: 2026-09-23 19:59:53.152527+00.
- **visual_potential**: 8.60 (confidence 0.720). purchase_trigger_v2 preliminary score; gate passed; trigger=shift_humor Дата: 2026-09-23 19:59:53.152527+00.

#### SPD — one dirty instrument
`v4_spd_everybody_back` · ID `d8de20a0-d7cb-4c0f-9fd9-1b98db03fe61`

**Интерпретация:** V4: редакционный финалист на выбор владельца, НЕ подтвержденное одобрение
**Статус БД:** shortlisted · **балл:** 92.29 · **confidence:** 70.32 · **coverage:** 100.00
**Текст / хук:** ONE OF YOU IS DIRTY. EVERYBODY GOES BACK.
**Идея:** Make one dirty instrument the guilty classmate that sends the entire tray back.
**Покупатель:** Sterile processing technicians
**Причина покупки:** Strong inside joke plus standards pride; it is easy to gift to an SPD tech.
**Отличие:** The humor comes from collective punishment, not instrument names.
**Визуальное направление:** Cartoon tray lineup with one guilty-looking generic instrument; no gore.
**Смысл для владельца (источник, EN):** If something in a set is still contaminated or otherwise fails inspection, the set cannot simply move forward as if everything were fine.
**Почему это шутка (источник, EN):** The line treats the instrument tray like a school class: one “dirty” member gets caught and everybody gets sent back. SPD workers recognize the frustration of one problem resetting work on a whole set.
**Создано / обновлено:** 2026-09-23 19:58:09.189566+00 / 2026-09-24 22:40:42.70901+00

Компоненты оценки:
- **buyer_desire**: 9.30 (confidence 0.700). purchase_trigger_v2 preliminary score; gate passed; trigger=standards_humor Дата: 2026-09-23 19:59:53.152527+00.
- **clarity_at_glance**: 9.30 (confidence 0.760). purchase_trigger_v2 preliminary score; gate passed; trigger=standards_humor Дата: 2026-09-23 19:59:53.152527+00.
- **distinctiveness**: 9.10 (confidence 0.700). purchase_trigger_v2 preliminary score; gate passed; trigger=standards_humor Дата: 2026-09-23 19:59:53.152527+00.
- **giftability**: 9.10 (confidence 0.670). purchase_trigger_v2 preliminary score; gate passed; trigger=standards_humor Дата: 2026-09-23 19:59:53.152527+00.
- **insider_resonance**: 9.50 (confidence 0.720). purchase_trigger_v2 preliminary score; gate passed; trigger=standards_humor Дата: 2026-09-23 19:59:53.152527+00.
- **ip_safety**: 8.80 (confidence 0.600). purchase_trigger_v2 preliminary score; gate passed; trigger=standards_humor Дата: 2026-09-23 19:59:53.152527+00.
- **niche_fit**: 9.50 (confidence 0.720). purchase_trigger_v2 preliminary score; gate passed; trigger=standards_humor Дата: 2026-09-23 19:59:53.152527+00.
- **visual_potential**: 9.00 (confidence 0.720). purchase_trigger_v2 preliminary score; gate passed; trigger=standards_humor Дата: 2026-09-23 19:59:53.152527+00.

#### SPD — you cannot rush the tray
`v4_spd_fanning_tray` · ID `83bb67e2-540e-4c06-85d7-4f979ef129c4`

**Интерпретация:** Исследовательский кандидат; одобрение владельца не зафиксировано
**Статус БД:** scored · **балл:** 88.95 · **confidence:** 70.32 · **coverage:** 100.00
**Текст / хук:** NO, WAVING AT IT WON'T MAKE IT READY.
**Идея:** Humor about people trying to speed a process that cannot safely be rushed.
**Покупатель:** Sterile processing technicians
**Причина покупки:** Funny boundary-setting around urgency versus required process time.
**Отличие:** No procedural checklist; the visual gag carries the culture.
**Визуальное направление:** Clipboard fanning a wrapped generic tray, with unimpressed SPD tech.
**Создано / обновлено:** 2026-09-23 19:58:09.189566+00 / 2026-09-24 05:05:38.621539+00

Компоненты оценки:
- **buyer_desire**: 8.80 (confidence 0.700). purchase_trigger_v2 preliminary score; gate passed; trigger=absurdity_humor Дата: 2026-09-23 19:59:53.152527+00.
- **clarity_at_glance**: 9.00 (confidence 0.760). purchase_trigger_v2 preliminary score; gate passed; trigger=absurdity_humor Дата: 2026-09-23 19:59:53.152527+00.
- **distinctiveness**: 8.90 (confidence 0.700). purchase_trigger_v2 preliminary score; gate passed; trigger=absurdity_humor Дата: 2026-09-23 19:59:53.152527+00.
- **giftability**: 8.60 (confidence 0.670). purchase_trigger_v2 preliminary score; gate passed; trigger=absurdity_humor Дата: 2026-09-23 19:59:53.152527+00.
- **insider_resonance**: 9.10 (confidence 0.720). purchase_trigger_v2 preliminary score; gate passed; trigger=absurdity_humor Дата: 2026-09-23 19:59:53.152527+00.
- **ip_safety**: 8.80 (confidence 0.600). purchase_trigger_v2 preliminary score; gate passed; trigger=absurdity_humor Дата: 2026-09-23 19:59:53.152527+00.
- **niche_fit**: 9.10 (confidence 0.720). purchase_trigger_v2 preliminary score; gate passed; trigger=absurdity_humor Дата: 2026-09-23 19:59:53.152527+00.
- **visual_potential**: 9.00 (confidence 0.720). purchase_trigger_v2 preliminary score; gate passed; trigger=absurdity_humor Дата: 2026-09-23 19:59:53.152527+00.

#### SPD — last line before the OR
`v4_spd_last_line` · ID `1dfb1d43-0e91-4da7-84c7-66beb1c87bb1`

**Интерпретация:** Исследовательский кандидат; одобрение владельца не зафиксировано
**Статус БД:** scored · **балл:** 86.81 · **confidence:** 70.32 · **coverage:** 100.00
**Текст / хук:** IF IT LEAVES HERE, I SIGN MY NAME TO IT.
**Идея:** A pride concept about the quiet responsibility of refusing shortcuts before instruments return to care.
**Покупатель:** Sterile processing technicians
**Причина покупки:** Professional ownership and seriousness rather than generic job-title pride.
**Отличие:** The message is accountability, not terminology.
**Визуальное направление:** Clean quality-control seal motif with a generic tray silhouette.
**Создано / обновлено:** 2026-09-23 19:58:09.189566+00 / 2026-09-24 05:05:38.621539+00

Компоненты оценки:
- **buyer_desire**: 8.50 (confidence 0.700). purchase_trigger_v2 preliminary score; gate passed; trigger=responsibility_pride Дата: 2026-09-23 19:59:53.152527+00.
- **clarity_at_glance**: 8.90 (confidence 0.760). purchase_trigger_v2 preliminary score; gate passed; trigger=responsibility_pride Дата: 2026-09-23 19:59:53.152527+00.
- **distinctiveness**: 8.50 (confidence 0.700). purchase_trigger_v2 preliminary score; gate passed; trigger=responsibility_pride Дата: 2026-09-23 19:59:53.152527+00.
- **giftability**: 8.30 (confidence 0.670). purchase_trigger_v2 preliminary score; gate passed; trigger=responsibility_pride Дата: 2026-09-23 19:59:53.152527+00.
- **insider_resonance**: 9.00 (confidence 0.720). purchase_trigger_v2 preliminary score; gate passed; trigger=responsibility_pride Дата: 2026-09-23 19:59:53.152527+00.
- **ip_safety**: 8.90 (confidence 0.600). purchase_trigger_v2 preliminary score; gate passed; trigger=responsibility_pride Дата: 2026-09-23 19:59:53.152527+00.
- **niche_fit**: 9.50 (confidence 0.720). purchase_trigger_v2 preliminary score; gate passed; trigger=responsibility_pride Дата: 2026-09-23 19:59:53.152527+00.
- **visual_potential**: 8.70 (confidence 0.720). purchase_trigger_v2 preliminary score; gate passed; trigger=responsibility_pride Дата: 2026-09-23 19:59:53.152527+00.

## 44. Substation / Relay Technician
Ключ: `substation_relay_technician` · ID: `3a4b94b7-6b06-4b0c-a88f-7ea62231cc41`

**Статус БД:** shortlisted · **балл:** 83.00 · **confidence:** 79.84 · **coverage:** 100.00
**Аудитория:** Powerhouse, substation and protective-relay electrical/electronics repairers
**Категория:** occupational_identity
**Исследовательская аргументация:** Small but fast-growing utility specialty with high pay, strong grid identity and exceptional visual language around relays, one-lines, breakers, CT/PT circuits, oscillography and protection logic. Sampled exact Etsy searches did not surface a dedicated relay-technician merch cluster.
**Создано / обновлено:** 2026-09-23 09:42:54.27545+00 / 2026-09-23 10:14:18.633101+00

### Компоненты оценки ниши

- **channel_breadth**: 7.50 (confidence 0.680). Forge hidden-trades v2 initial score using current BLS/O*NET occupational evidence plus sampled Etsy marketplace depth. Scores prioritize buyer identity and whitespace, not raw occupation size. Benchmark niches intentionally receive competition penalties. Utility, contractor, data-center/grid-expansion and substation contexts broaden applicability beyond one employer/channel. Дата: 2026-09-23 09:43:36.792084+00.
- **competition_opportunity**: 9.00 (confidence 0.680). Forge hidden-trades v2 initial score using current BLS/O*NET occupational evidence plus sampled Etsy marketplace depth. Scores prioritize buyer identity and whitespace, not raw occupation size. Benchmark niches intentionally receive competition penalties. A current Etsy Substation Technician shirt exists, proving some merch demand, but sampled search did not show a mass category comparable with lineman merch; whitespace confidence is moderate. Дата: 2026-09-23 09:43:36.792084+00.
- **concept_depth**: 9.50 (confidence 0.840). Forge hidden-trades v2 initial score using current BLS/O*NET occupational evidence plus sampled Etsy marketplace depth. Scores prioritize buyer identity and whitespace, not raw occupation size. Benchmark niches intentionally receive competition penalties. Practitioner evidence supports protection schemes, relay testing/settings, commissioning, sequence-of-events, wiring/logic diagnostics, CT/PT circuits and breaker trip/control concepts. Дата: 2026-09-23 09:43:36.792084+00.
- **demand_evidence**: 8.20 (confidence 0.940). Forge hidden-trades v2 initial score using current BLS/O*NET occupational evidence plus sampled Etsy marketplace depth. Scores prioritize buyer identity and whitespace, not raw occupation size. Benchmark niches intentionally receive competition penalties. BLS directly reports 20,900 powerhouse/substation/relay repairer jobs in 2025, projected to 22,900 by 2035 (~9.7% growth), and explicitly links demand to grid strain; Sep 2026 practitioners also report retirements and shortage of qualified relay/P&C talent. Дата: 2026-09-23 09:43:36.792084+00.
- **founder_edge**: 2.00 (confidence 0.400). Forge hidden-trades v2 initial score using current BLS/O*NET occupational evidence plus sampled Etsy marketplace depth. Scores prioritize buyer identity and whitespace, not raw occupation size. Benchmark niches intentionally receive competition penalties. Дата: 2026-09-23 09:43:36.792084+00.
- **identity_intensity**: 8.00 (confidence 0.840). Forge hidden-trades v2 initial score using current BLS/O*NET occupational evidence plus sampled Etsy marketplace depth. Scores prioritize buyer identity and whitespace, not raw occupation size. Benchmark niches intentionally receive competition penalties. Current SubstationTechnician discussions show a distinct relay/P&C apprenticeship, skill ladder and practitioner identity separate from generic electricians/linemen. Дата: 2026-09-23 09:43:36.792084+00.
- **legal_safety**: 9.00 (confidence 0.660). Forge hidden-trades v2 initial score using current BLS/O*NET occupational evidence plus sampled Etsy marketplace depth. Scores prioritize buyer identity and whitespace, not raw occupation size. Benchmark niches intentionally receive competition penalties. Дата: 2026-09-23 09:43:36.792084+00.
- **purchase_motivation**: 7.50 (confidence 0.760). Forge hidden-trades v2 initial score using current BLS/O*NET occupational evidence plus sampled Etsy marketplace depth. Scores prioritize buyer identity and whitespace, not raw occupation size. Benchmark niches intentionally receive competition penalties. Strong professional scarcity, apprenticeship culture and technical specialization support identity/gift motivation; still indirect sales evidence. Дата: 2026-09-23 09:43:36.792084+00.
- **repeatability**: 8.00 (confidence 0.740). Forge hidden-trades v2 initial score using current BLS/O*NET occupational evidence plus sampled Etsy marketplace depth. Scores prioritize buyer identity and whitespace, not raw occupation size. Benchmark niches intentionally receive competition penalties. Protection/control work has multiple authentic system and diagnostic subthemes, supporting repeat series. Дата: 2026-09-23 09:43:36.792084+00.
- **visual_language**: 9.50 (confidence 0.860). Forge hidden-trades v2 initial score using current BLS/O*NET occupational evidence plus sampled Etsy marketplace depth. Scores prioritize buyer identity and whitespace, not raw occupation size. Benchmark niches intentionally receive competition penalties. One-lines, relay logic, breaker/trip paths, CT/PT circuits, oscillography and control wiring provide a highly specific visual grammar. Дата: 2026-09-23 09:43:36.792084+00.

### Концепции (11)

#### Relay — CT/PT to trip chain
`relay_ct_pt_logic_trip_chain` · ID `de018ff3-8bda-48ed-a5a9-56a82c3fc353`

**Интерпретация:** Исторический: снят после owner review; не возвращать автоматически
**Статус БД:** scored · **балл:** 88.97 · **confidence:** 69.17 · **coverage:** 100.00
**Текст / хук:** CT/PT → RELAY → LOGIC → TRIP
**Идея:** Relay — CT/PT to trip chain. Core hook: CT/PT → RELAY → LOGIC → TRIP. Protection and control work: test circuits, troubleshoot relays, analyze data, maintain relay/control systems. Execution must stay original and descriptive; avoid employer, OEM, certification-body, association and proprietary-interface branding.
**Покупатель:** Powerhouse/substation relay technicians
**Причина покупки:** Identity purchase for powerhouse/substation relay technicians who recognize the real workflow/systems language.
**Отличие:** Insider technical system map direction intended to avoid generic profession-title, retro-badge, skull, flag, coffee and parody templates.
**Визуальное направление:** Abstract protection chain connecting instrument transformers, relay logic and breaker trip output.
**retired_reason:** failed purchase-trigger quality bar after owner review
**Создано / обновлено:** 2026-09-23 09:48:50.541446+00 / 2026-09-23 23:40:31.847823+00

Компоненты оценки:
- **buyer_desire**: 8.63 (confidence 0.680). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **clarity_at_glance**: 8.20 (confidence 0.680). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **distinctiveness**: 9.10 (confidence 0.680). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **giftability**: 7.60 (confidence 0.680). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **insider_resonance**: 9.15 (confidence 0.710). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **ip_safety**: 8.80 (confidence 0.680). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **niche_fit**: 9.40 (confidence 0.710). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **visual_potential**: 9.65 (confidence 0.710). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.

#### Relay — event sequence
`relay_event_sequence_trip_clear` · ID `423bcad9-68a8-4367-85fe-ee9df6c205eb`

**Интерпретация:** Исследовательский кандидат; одобрение владельца не зафиксировано
**Статус БД:** scored · **балл:** 88.36 · **confidence:** 68.17 · **coverage:** 100.00
**Текст / хук:** EVENT → TARGET → TRIP → CLEAR
**Идея:** Relay — event sequence. Core hook: EVENT → TARGET → TRIP → CLEAR. Protection and control work: test circuits, troubleshoot relays, analyze data, maintain relay/control systems. Execution must stay original and descriptive; avoid employer, OEM, certification-body, association and proprietary-interface branding.
**Покупатель:** Powerhouse/substation relay technicians
**Причина покупки:** Identity purchase for powerhouse/substation relay technicians who recognize the real workflow/systems language.
**Отличие:** Insider technical technical map direction intended to avoid generic profession-title, retro-badge, skull, flag, coffee and parody templates.
**Визуальное направление:** Sequence-of-events / oscillography-inspired timeline rendered as original waveform geometry and event markers.
**Создано / обновлено:** 2026-09-23 09:48:50.541446+00 / 2026-09-23 09:55:40.114238+00

Компоненты оценки:
- **buyer_desire**: 8.43 (confidence 0.670). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **clarity_at_glance**: 7.77 (confidence 0.670). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **distinctiveness**: 9.20 (confidence 0.670). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **giftability**: 7.47 (confidence 0.670). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **insider_resonance**: 9.30 (confidence 0.700). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **ip_safety**: 8.60 (confidence 0.670). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **niche_fit**: 9.40 (confidence 0.700). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **visual_potential**: 9.60 (confidence 0.700). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.

#### Relay — fault to trip path
`relay_fault_trip_breaker_path` · ID `42023ae6-8cae-44f6-9014-df27950cc978`

**Интерпретация:** Исторический: снят после owner review; не возвращать автоматически
**Статус БД:** scored · **балл:** 88.97 · **confidence:** 68.17 · **coverage:** 100.00
**Текст / хук:** FAULT → RELAY → TRIP → BREAKER
**Идея:** Relay — fault to trip path. Core hook: FAULT → RELAY → TRIP → BREAKER. Protection and control work: test circuits, troubleshoot relays, analyze data, maintain relay/control systems. Execution must stay original and descriptive; avoid employer, OEM, certification-body, association and proprietary-interface branding.
**Покупатель:** Powerhouse/substation relay technicians
**Причина покупки:** Identity purchase for powerhouse/substation relay technicians who recognize the real workflow/systems language.
**Отличие:** Insider technical technical map direction intended to avoid generic profession-title, retro-badge, skull, flag, coffee and parody templates.
**Визуальное направление:** Original one-line-style protection path with a generic fault point, relay block, trip circuit and breaker; no utility or OEM symbols copied.
**retired_reason:** failed purchase-trigger quality bar after owner review
**Создано / обновлено:** 2026-09-23 09:48:50.541446+00 / 2026-09-23 23:40:31.847823+00

Компоненты оценки:
- **buyer_desire**: 8.53 (confidence 0.670). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **clarity_at_glance**: 7.80 (confidence 0.670). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **distinctiveness**: 9.30 (confidence 0.670). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **giftability**: 7.50 (confidence 0.670). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **insider_resonance**: 9.35 (confidence 0.700). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **ip_safety**: 8.60 (confidence 0.670). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **niche_fit**: 9.40 (confidence 0.700). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **visual_potential**: 9.65 (confidence 0.700). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.

#### Relay — test / compare / verify
`relay_inject_measure_compare_verify` · ID `6bea3fd6-f175-40ec-bff8-7150c6b2f665`

**Интерпретация:** Исследовательский кандидат; одобрение владельца не зафиксировано
**Статус БД:** scored · **балл:** 88.94 · **confidence:** 69.17 · **coverage:** 100.00
**Текст / хук:** INJECT • MEASURE • COMPARE • VERIFY
**Идея:** Relay — test / compare / verify. Core hook: INJECT • MEASURE • COMPARE • VERIFY. Protection and control work: test circuits, troubleshoot relays, analyze data, maintain relay/control systems. Execution must stay original and descriptive; avoid employer, OEM, certification-body, association and proprietary-interface branding.
**Покупатель:** Powerhouse/substation relay technicians
**Причина покупки:** Identity purchase for powerhouse/substation relay technicians who recognize the real workflow/systems language.
**Отличие:** Insider technical diagnostic direction intended to avoid generic profession-title, retro-badge, skull, flag, coffee and parody templates.
**Визуальное направление:** Generic relay-test-set motif with traces and result blocks; technical service aesthetic, not a real vendor screen.
**Создано / обновлено:** 2026-09-23 09:48:50.541446+00 / 2026-09-23 09:55:40.114238+00

Компоненты оценки:
- **buyer_desire**: 8.73 (confidence 0.680). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **clarity_at_glance**: 8.57 (confidence 0.680). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **distinctiveness**: 9.00 (confidence 0.680). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **giftability**: 7.87 (confidence 0.680). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **insider_resonance**: 9.40 (confidence 0.710). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **ip_safety**: 8.70 (confidence 0.680). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **niche_fit**: 9.50 (confidence 0.710). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **visual_potential**: 8.90 (confidence 0.710). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.

#### Relay — trace / isolate / restore
`relay_trace_isolate_test_restore` · ID `f1c27507-0aae-45a3-95ce-65d1af18d66a`

**Интерпретация:** Исследовательский кандидат; одобрение владельца не зафиксировано
**Статус БД:** scored · **балл:** 85.22 · **confidence:** 67.17 · **coverage:** 100.00
**Текст / хук:** TRACE • ISOLATE • TEST • RESTORE
**Идея:** Relay — trace / isolate / restore. Core hook: TRACE • ISOLATE • TEST • RESTORE. Protection and control work: test circuits, troubleshoot relays, analyze data, maintain relay/control systems. Execution must stay original and descriptive; avoid employer, OEM, certification-body, association and proprietary-interface branding.
**Покупатель:** Powerhouse/substation relay technicians
**Причина покупки:** Identity purchase for powerhouse/substation relay technicians who recognize the real workflow/systems language.
**Отличие:** Insider technical workflow direction intended to avoid generic profession-title, retro-badge, skull, flag, coffee and parody templates.
**Визуальное направление:** Troubleshooting workflow around generic schematics, test points and a relay/control cabinet silhouette.
**Создано / обновлено:** 2026-09-23 09:48:50.541446+00 / 2026-09-23 09:55:40.114238+00

Компоненты оценки:
- **buyer_desire**: 8.23 (confidence 0.660). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **clarity_at_glance**: 9.13 (confidence 0.660). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **distinctiveness**: 8.30 (confidence 0.660). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **giftability**: 8.03 (confidence 0.660). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **insider_resonance**: 8.75 (confidence 0.690). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **ip_safety**: 9.00 (confidence 0.660). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **niche_fit**: 9.30 (confidence 0.690). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **visual_potential**: 8.35 (confidence 0.690). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.

#### Substation — breaker / relay / DC control
`substation_breaker_relay_dc_control` · ID `9ca47dce-b1dd-46c4-b938-5129a0ea453e`

**Интерпретация:** Исследовательский кандидат; одобрение владельца не зафиксировано
**Статус БД:** scored · **балл:** 88.36 · **confidence:** 69.17 · **coverage:** 100.00
**Текст / хук:** BREAKER • RELAY • CONTROL • DC
**Идея:** Substation — breaker / relay / DC control. Core hook: BREAKER • RELAY • CONTROL • DC. Protection and control work: test circuits, troubleshoot relays, analyze data, maintain relay/control systems. Execution must stay original and descriptive; avoid employer, OEM, certification-body, association and proprietary-interface branding.
**Покупатель:** Powerhouse/substation relay technicians
**Причина покупки:** Identity purchase for powerhouse/substation relay technicians who recognize the real workflow/systems language.
**Отличие:** Insider technical system map direction intended to avoid generic profession-title, retro-badge, skull, flag, coffee and parody templates.
**Визуальное направление:** Four-system substation service stack with original breaker, relay, control and DC-control blocks.
**Создано / обновлено:** 2026-09-23 09:48:50.541446+00 / 2026-09-23 09:55:40.114238+00

Компоненты оценки:
- **buyer_desire**: 8.53 (confidence 0.680). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **clarity_at_glance**: 8.17 (confidence 0.680). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **distinctiveness**: 9.00 (confidence 0.680). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **giftability**: 7.57 (confidence 0.680). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **insider_resonance**: 9.10 (confidence 0.710). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **ip_safety**: 8.80 (confidence 0.680). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **niche_fit**: 9.40 (confidence 0.710). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **visual_potential**: 9.60 (confidence 0.710). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.

#### Relay tech — protection is boring until it matters
`v4_relay_boring_until` · ID `df7cf8ad-a54d-45cb-b3eb-a8a0499f6b5f`

**Интерпретация:** V4: понижен редакционным отбором, сохранен в истории
**Статус БД:** scored · **балл:** 85.10 · **confidence:** 70.32 · **coverage:** 100.00
**Текст / хук:** PROTECTION IS BORING. UNTIL IT ISN'T.
**Идея:** Pride in invisible preventive systems that matter only during rare failures.
**Покупатель:** Substation / protective-relay technicians
**Причина покупки:** Identity statement for a quiet specialty with huge consequence.
**Отличие:** Not a workflow list; value comes from the tension between invisibility and importance.
**Визуальное направление:** Calm flatline-style grid suddenly turning into a dramatic trip event.
**editorial_reason:** generic rhetorical construction
**Создано / обновлено:** 2026-09-23 19:58:09.189566+00 / 2026-09-24 05:05:38.621539+00

Компоненты оценки:
- **buyer_desire**: 8.20 (confidence 0.700). purchase_trigger_v2 preliminary score; gate passed; trigger=invisible_work_pride Дата: 2026-09-23 19:59:53.152527+00.
- **clarity_at_glance**: 8.80 (confidence 0.760). purchase_trigger_v2 preliminary score; gate passed; trigger=invisible_work_pride Дата: 2026-09-23 19:59:53.152527+00.
- **distinctiveness**: 8.20 (confidence 0.700). purchase_trigger_v2 preliminary score; gate passed; trigger=invisible_work_pride Дата: 2026-09-23 19:59:53.152527+00.
- **giftability**: 8.10 (confidence 0.670). purchase_trigger_v2 preliminary score; gate passed; trigger=invisible_work_pride Дата: 2026-09-23 19:59:53.152527+00.
- **insider_resonance**: 8.90 (confidence 0.720). purchase_trigger_v2 preliminary score; gate passed; trigger=invisible_work_pride Дата: 2026-09-23 19:59:53.152527+00.
- **ip_safety**: 8.90 (confidence 0.600). purchase_trigger_v2 preliminary score; gate passed; trigger=invisible_work_pride Дата: 2026-09-23 19:59:53.152527+00.
- **niche_fit**: 9.40 (confidence 0.720). purchase_trigger_v2 preliminary score; gate passed; trigger=invisible_work_pride Дата: 2026-09-23 19:59:53.152527+00.
- **visual_potential**: 8.80 (confidence 0.720). purchase_trigger_v2 preliminary score; gate passed; trigger=invisible_work_pride Дата: 2026-09-23 19:59:53.152527+00.

#### Relay tech — the button nobody wants to touch
`v4_relay_button` · ID `57e4e8c4-2937-49c0-a661-b000445eee51`

**Интерпретация:** Исследовательский кандидат; одобрение владельца не зафиксировано
**Статус БД:** scored · **балл:** 89.10 · **confidence:** 70.32 · **coverage:** 100.00
**Текст / хук:** I TEST THE BUTTON EVERYONE ELSE IS AFRAID TO TOUCH.
**Идея:** Pride/humor around intentionally testing trip paths that everyone else treats with fear.
**Покупатель:** Substation / protective-relay technicians
**Причина покупки:** High-status specialist identity with obvious insider reaction.
**Отличие:** The hook is responsibility and nerve, not relay jargon.
**Визуальное направление:** Large guarded red switch / gloved hand; generic, no utility branding.
**Создано / обновлено:** 2026-09-23 19:58:09.189566+00 / 2026-09-24 05:05:38.621539+00

Компоненты оценки:
- **buyer_desire**: 8.70 (confidence 0.700). purchase_trigger_v2 preliminary score; gate passed; trigger=high_consequence_pride Дата: 2026-09-23 19:59:53.152527+00.
- **clarity_at_glance**: 9.00 (confidence 0.760). purchase_trigger_v2 preliminary score; gate passed; trigger=high_consequence_pride Дата: 2026-09-23 19:59:53.152527+00.
- **distinctiveness**: 8.90 (confidence 0.700). purchase_trigger_v2 preliminary score; gate passed; trigger=high_consequence_pride Дата: 2026-09-23 19:59:53.152527+00.
- **giftability**: 8.50 (confidence 0.670). purchase_trigger_v2 preliminary score; gate passed; trigger=high_consequence_pride Дата: 2026-09-23 19:59:53.152527+00.
- **insider_resonance**: 9.30 (confidence 0.720). purchase_trigger_v2 preliminary score; gate passed; trigger=high_consequence_pride Дата: 2026-09-23 19:59:53.152527+00.
- **ip_safety**: 8.90 (confidence 0.600). purchase_trigger_v2 preliminary score; gate passed; trigger=high_consequence_pride Дата: 2026-09-23 19:59:53.152527+00.
- **niche_fit**: 9.50 (confidence 0.720). purchase_trigger_v2 preliminary score; gate passed; trigger=high_consequence_pride Дата: 2026-09-23 19:59:53.152527+00.
- **visual_potential**: 9.00 (confidence 0.720). purchase_trigger_v2 preliminary score; gate passed; trigger=high_consequence_pride Дата: 2026-09-23 19:59:53.152527+00.

#### Relay tech — one click, large meeting
`v4_relay_large_meeting` · ID `e4a77f02-5c8d-4d66-add0-7783a11659f4`

**Интерпретация:** V4: редакционный финалист на выбор владельца, НЕ подтвержденное одобрение
**Статус БД:** shortlisted · **балл:** 93.72 · **confidence:** 70.32 · **coverage:** 100.00
**Текст / хук:** ONE CLICK AWAY FROM A VERY LARGE MEETING.
**Идея:** Gallows humor about the organizational consequences of one wrong action.
**Покупатель:** Substation / protective-relay technicians
**Причина покупки:** Memorable high-consequence workplace humor with strong coworker gift appeal.
**Отличие:** No technical list; the joke is consequence disproportion.
**Визуальное направление:** Tiny switch casting a huge conference-room shadow.
**Смысл для владельца (источник, EN):** The line says that one tiny click can create consequences big enough to trigger a serious incident review or a room full of people asking what happened.
**Почему это шутка (источник, EN):** The humor is the absurd mismatch between the size of the action and the size of the organizational fallout. Relay technicians immediately understand why a seemingly small action can make everyone very interested very quickly.
**Создано / обновлено:** 2026-09-23 19:58:09.189566+00 / 2026-09-24 22:40:42.70901+00

Компоненты оценки:
- **buyer_desire**: 9.50 (confidence 0.700). purchase_trigger_v2 preliminary score; gate passed; trigger=consequence_humor Дата: 2026-09-23 19:59:53.152527+00.
- **clarity_at_glance**: 9.50 (confidence 0.760). purchase_trigger_v2 preliminary score; gate passed; trigger=consequence_humor Дата: 2026-09-23 19:59:53.152527+00.
- **distinctiveness**: 9.40 (confidence 0.700). purchase_trigger_v2 preliminary score; gate passed; trigger=consequence_humor Дата: 2026-09-23 19:59:53.152527+00.
- **giftability**: 9.30 (confidence 0.670). purchase_trigger_v2 preliminary score; gate passed; trigger=consequence_humor Дата: 2026-09-23 19:59:53.152527+00.
- **insider_resonance**: 9.50 (confidence 0.720). purchase_trigger_v2 preliminary score; gate passed; trigger=consequence_humor Дата: 2026-09-23 19:59:53.152527+00.
- **ip_safety**: 8.80 (confidence 0.600). purchase_trigger_v2 preliminary score; gate passed; trigger=consequence_humor Дата: 2026-09-23 19:59:53.152527+00.
- **niche_fit**: 9.30 (confidence 0.720). purchase_trigger_v2 preliminary score; gate passed; trigger=consequence_humor Дата: 2026-09-23 19:59:53.152527+00.
- **visual_potential**: 9.10 (confidence 0.720). purchase_trigger_v2 preliminary score; gate passed; trigger=consequence_humor Дата: 2026-09-23 19:59:53.152527+00.

#### Relay tech — keeping lights on by testing trips
`v4_relay_lights_on` · ID `844ce889-9004-4a4e-90df-4d65982df31f`

**Интерпретация:** Исследовательский кандидат; одобрение владельца не зафиксировано
**Статус БД:** scored · **балл:** 85.71 · **confidence:** 70.32 · **coverage:** 100.00
**Текст / хук:** KEEPING THE LIGHTS ON BY PROVING THEY CAN TURN OFF.
**Идея:** Paradoxical pride: proving protection can turn things off is how you keep them on safely.
**Покупатель:** Substation / protective-relay technicians
**Причина покупки:** Pride plus clever paradox; suitable for wearer and gift buyer.
**Отличие:** A human/commercial idea with technical truth underneath.
**Визуальное направление:** Lit skyline on one side, relay test switch on the other.
**Создано / обновлено:** 2026-09-23 19:58:09.189566+00 / 2026-09-24 05:05:38.621539+00

Компоненты оценки:
- **buyer_desire**: 8.40 (confidence 0.700). purchase_trigger_v2 preliminary score; gate passed; trigger=professional_pride Дата: 2026-09-23 19:59:53.152527+00.
- **clarity_at_glance**: 8.80 (confidence 0.760). purchase_trigger_v2 preliminary score; gate passed; trigger=professional_pride Дата: 2026-09-23 19:59:53.152527+00.
- **distinctiveness**: 8.30 (confidence 0.700). purchase_trigger_v2 preliminary score; gate passed; trigger=professional_pride Дата: 2026-09-23 19:59:53.152527+00.
- **giftability**: 8.20 (confidence 0.670). purchase_trigger_v2 preliminary score; gate passed; trigger=professional_pride Дата: 2026-09-23 19:59:53.152527+00.
- **insider_resonance**: 8.90 (confidence 0.720). purchase_trigger_v2 preliminary score; gate passed; trigger=professional_pride Дата: 2026-09-23 19:59:53.152527+00.
- **ip_safety**: 8.90 (confidence 0.600). purchase_trigger_v2 preliminary score; gate passed; trigger=professional_pride Дата: 2026-09-23 19:59:53.152527+00.
- **niche_fit**: 9.40 (confidence 0.720). purchase_trigger_v2 preliminary score; gate passed; trigger=professional_pride Дата: 2026-09-23 19:59:53.152527+00.
- **visual_potential**: 8.60 (confidence 0.720). purchase_trigger_v2 preliminary score; gate passed; trigger=professional_pride Дата: 2026-09-23 19:59:53.152527+00.

#### Relay tech — professionally making people nervous
`v4_relay_nervous` · ID `80ef40dc-a341-4e5b-a0a2-0de0fbc8f55e`

**Интерпретация:** V4: редакционный финалист на выбор владельца, НЕ подтвержденное одобрение
**Статус БД:** shortlisted · **балл:** 89.29 · **confidence:** 70.32 · **coverage:** 100.00
**Текст / хук:** TRIP TEST: PROFESSIONALLY MAKING PEOPLE NERVOUS.
**Идея:** Humor about trip testing making everyone nearby tense even when done correctly.
**Покупатель:** Substation / protective-relay technicians
**Причина покупки:** Social humor and specialist identity.
**Отличие:** The concept centers other people's reaction, not test-step jargon.
**Визуальное направление:** Nervous observers behind a calm technician at a test set.
**Смысл для владельца (источник, EN):** A trip test is routine professional work for the technician, but everyone nearby knows that “trip” is connected to opening breakers and taking equipment out of service.
**Почему это шутка (источник, EN):** The technician is calm because this is normal work; observers are tense because they understand the consequences if something happens unexpectedly. The humor is being professionally responsible for making the room nervous.
**Создано / обновлено:** 2026-09-23 19:58:09.189566+00 / 2026-09-24 22:40:42.70901+00

Компоненты оценки:
- **buyer_desire**: 8.90 (confidence 0.700). purchase_trigger_v2 preliminary score; gate passed; trigger=social_reaction_humor Дата: 2026-09-23 19:59:53.152527+00.
- **clarity_at_glance**: 9.10 (confidence 0.760). purchase_trigger_v2 preliminary score; gate passed; trigger=social_reaction_humor Дата: 2026-09-23 19:59:53.152527+00.
- **distinctiveness**: 8.70 (confidence 0.700). purchase_trigger_v2 preliminary score; gate passed; trigger=social_reaction_humor Дата: 2026-09-23 19:59:53.152527+00.
- **giftability**: 8.80 (confidence 0.670). purchase_trigger_v2 preliminary score; gate passed; trigger=social_reaction_humor Дата: 2026-09-23 19:59:53.152527+00.
- **insider_resonance**: 9.20 (confidence 0.720). purchase_trigger_v2 preliminary score; gate passed; trigger=social_reaction_humor Дата: 2026-09-23 19:59:53.152527+00.
- **ip_safety**: 8.90 (confidence 0.600). purchase_trigger_v2 preliminary score; gate passed; trigger=social_reaction_humor Дата: 2026-09-23 19:59:53.152527+00.
- **niche_fit**: 9.30 (confidence 0.720). purchase_trigger_v2 preliminary score; gate passed; trigger=social_reaction_humor Дата: 2026-09-23 19:59:53.152527+00.
- **visual_potential**: 8.80 (confidence 0.720). purchase_trigger_v2 preliminary score; gate passed; trigger=social_reaction_humor Дата: 2026-09-23 19:59:53.152527+00.

## 45. Surgical Technologist / Scrub Tech
Ключ: `surgical_technologist` · ID: `e69fa963-a957-46d0-b351-c4583bfee7b5`

**Статус БД:** scored · **балл:** 75.95 · **confidence:** 82.78 · **coverage:** 100.00
**Аудитория:** Surgical technologists / scrub techs
**Категория:** occupational_identity
**Исследовательская аргументация:** Large identifiable healthcare-tech occupation with strong instrument/sterile-field language, but current Etsy competition is very high. Retained as a high-demand/saturated benchmark, not a whitespace candidate.
**Создано / обновлено:** 2026-09-23 09:56:40.513406+00 / 2026-09-23 23:52:40.297494+00

### Компоненты оценки ниши

- **channel_breadth**: 8.00 (confidence 0.660). Forge diversity-batch v3 score using current 2025-35 BLS/O*NET evidence plus sampled current Etsy competition. Where exact marketplace counts were unavailable, competition confidence is intentionally lower. Дата: 2026-09-23 09:56:40.513406+00.
- **competition_opportunity**: 1.50 (confidence 0.960). Forge diversity-batch v3 score using current 2025-35 BLS/O*NET evidence plus sampled current Etsy competition. Where exact marketplace counts were unavailable, competition confidence is intentionally lower. Дата: 2026-09-23 09:56:40.513406+00.
- **concept_depth**: 8.50 (confidence 0.760). Forge diversity-batch v3 score using current 2025-35 BLS/O*NET evidence plus sampled current Etsy competition. Where exact marketplace counts were unavailable, competition confidence is intentionally lower. Дата: 2026-09-23 09:56:40.513406+00.
- **demand_evidence**: 9.00 (confidence 0.940). Forge diversity-batch v3 score using current 2025-35 BLS/O*NET evidence plus sampled current Etsy competition. Where exact marketplace counts were unavailable, competition confidence is intentionally lower. Дата: 2026-09-23 09:56:40.513406+00.
- **founder_edge**: 2.00 (confidence 0.400). Forge diversity-batch v3 score using current 2025-35 BLS/O*NET evidence plus sampled current Etsy competition. Where exact marketplace counts were unavailable, competition confidence is intentionally lower. Дата: 2026-09-23 09:56:40.513406+00.
- **identity_intensity**: 9.00 (confidence 0.820). Forge diversity-batch v3 score using current 2025-35 BLS/O*NET evidence plus sampled current Etsy competition. Where exact marketplace counts were unavailable, competition confidence is intentionally lower. Дата: 2026-09-23 09:56:40.513406+00.
- **legal_safety**: 8.00 (confidence 0.620). Forge diversity-batch v3 score using current 2025-35 BLS/O*NET evidence plus sampled current Etsy competition. Where exact marketplace counts were unavailable, competition confidence is intentionally lower. Дата: 2026-09-23 09:56:40.513406+00.
- **purchase_motivation**: 9.00 (confidence 0.800). Forge diversity-batch v3 score using current 2025-35 BLS/O*NET evidence plus sampled current Etsy competition. Where exact marketplace counts were unavailable, competition confidence is intentionally lower. Дата: 2026-09-23 09:56:40.513406+00.
- **repeatability**: 9.00 (confidence 0.760). Forge diversity-batch v3 score using current 2025-35 BLS/O*NET evidence plus sampled current Etsy competition. Where exact marketplace counts were unavailable, competition confidence is intentionally lower. Дата: 2026-09-23 09:56:40.513406+00.
- **visual_language**: 9.00 (confidence 0.800). Forge diversity-batch v3 score using current 2025-35 BLS/O*NET evidence plus sampled current Etsy competition. Where exact marketplace counts were unavailable, competition confidence is intentionally lower. Дата: 2026-09-23 09:56:40.513406+00.

### Концепции (0)

## 46. Surveying & Mapping Technician
Ключ: `survey_mapping_technician` · ID: `f6fdd529-b52f-4a50-92ec-e2991b4e36da`

**Статус БД:** scored · **балл:** 74.35 · **confidence:** 75.44 · **coverage:** 100.00
**Аудитория:** Surveying and mapping technicians
**Категория:** occupational_identity
**Исследовательская аргументация:** Legacy Town Label occupational niche carried forward for re-evaluation under the new niche-first scoring engine. Existing artwork quality does not determine niche status.
**Создано / обновлено:** 2026-09-23 06:11:01.997287+00 / 2026-09-23 09:44:55.053118+00

### Компоненты оценки ниши

- **channel_breadth**: 8.00 (confidence 0.660). Legacy Forge/Town Label niche rescored under the unified Forge rubric using current 2025-35 BLS data plus the 2026-09-21/22 marketplace and IP research already stored in merch.research_notes. Existing visual rejection does not count as niche rejection. Дата: 2026-09-23 09:44:55.053118+00.
- **competition_opportunity**: 4.50 (confidence 0.780). Legacy Forge/Town Label niche rescored under the unified Forge rubric using current 2025-35 BLS data plus the 2026-09-21/22 marketplace and IP research already stored in merch.research_notes. Existing visual rejection does not count as niche rejection. Дата: 2026-09-23 09:44:55.053118+00.
- **concept_depth**: 9.00 (confidence 0.780). Legacy Forge/Town Label niche rescored under the unified Forge rubric using current 2025-35 BLS data plus the 2026-09-21/22 marketplace and IP research already stored in merch.research_notes. Existing visual rejection does not count as niche rejection. Дата: 2026-09-23 09:44:55.053118+00.
- **demand_evidence**: 7.50 (confidence 0.900). Legacy Forge/Town Label niche rescored under the unified Forge rubric using current 2025-35 BLS data plus the 2026-09-21/22 marketplace and IP research already stored in merch.research_notes. Existing visual rejection does not count as niche rejection. Дата: 2026-09-23 09:44:55.053118+00.
- **founder_edge**: 2.00 (confidence 0.400). Legacy Forge/Town Label niche rescored under the unified Forge rubric using current 2025-35 BLS data plus the 2026-09-21/22 marketplace and IP research already stored in merch.research_notes. Existing visual rejection does not count as niche rejection. Дата: 2026-09-23 09:44:55.053118+00.
- **identity_intensity**: 8.00 (confidence 0.700). Legacy Forge/Town Label niche rescored under the unified Forge rubric using current 2025-35 BLS data plus the 2026-09-21/22 marketplace and IP research already stored in merch.research_notes. Existing visual rejection does not count as niche rejection. Дата: 2026-09-23 09:44:55.053118+00.
- **legal_safety**: 8.50 (confidence 0.720). Legacy Forge/Town Label niche rescored under the unified Forge rubric using current 2025-35 BLS data plus the 2026-09-21/22 marketplace and IP research already stored in merch.research_notes. Existing visual rejection does not count as niche rejection. Дата: 2026-09-23 09:44:55.053118+00.
- **purchase_motivation**: 7.50 (confidence 0.640). Legacy Forge/Town Label niche rescored under the unified Forge rubric using current 2025-35 BLS data plus the 2026-09-21/22 marketplace and IP research already stored in merch.research_notes. Existing visual rejection does not count as niche rejection. Дата: 2026-09-23 09:44:55.053118+00.
- **repeatability**: 8.00 (confidence 0.660). Legacy Forge/Town Label niche rescored under the unified Forge rubric using current 2025-35 BLS data plus the 2026-09-21/22 marketplace and IP research already stored in merch.research_notes. Existing visual rejection does not count as niche rejection. Дата: 2026-09-23 09:44:55.053118+00.
- **visual_language**: 9.50 (confidence 0.840). Legacy Forge/Town Label niche rescored under the unified Forge rubric using current 2025-35 BLS data plus the 2026-09-21/22 marketplace and IP research already stored in merch.research_notes. Existing visual rejection does not count as niche rejection. Дата: 2026-09-23 09:44:55.053118+00.

### Концепции (1)

#### Surveying — field data to map data
`survey_field_to_map` · ID `e5efbdbb-729c-4275-9a17-547762f8c87d`

**Интерпретация:** Исследовательский кандидат; одобрение владельца не зафиксировано
**Статус БД:** scored · **балл:** 89.07 · **confidence:** 73.26 · **coverage:** 100.00
**Текст / хук:** FIELD DATA → MAP DATA
**Идея:** Surveying & Mapping Technician professional field-to-map data graphic using the full occupational title plus ANGLES • ELEVATIONS • GIS, MEASURE • RECORD • PROCESS • MAP, and FIELD DATA → MAP DATA. Research proof A uses an original measurement-to-grid schematic instead of total-station clipart, compass badges, retro sunsets, or generic surveyor jokes.
**Покупатель:** Surveying and mapping technicians
**Отличие:** Generic surveyor apparel is established and crowded with tripod/total-station graphics, badges, definitions, jokes and retro designs; exact surveying-and-mapping technician identity is less represented.
**Создано / обновлено:** 2026-09-23 06:11:42.741293+00 / 2026-09-23 09:57:07.855981+00

Компоненты оценки:
- **buyer_desire**: 8.32 (confidence 0.729). Unified Forge concept-depth score. Profile captures the concept form (technical map, diagnostic, system map, workflow, process or terminology); a small stored concept bias and bounded niche-quality adjustment prevent identical form scores across materially different niches. No visual was generated. Federal/common-law phrase review remains a separate gate. Дата: 2026-09-23 09:51:32.257179+00.
- **clarity_at_glance**: 8.10 (confidence 0.706). Unified Forge concept-depth score. Profile captures the concept form (technical map, diagnostic, system map, workflow, process or terminology); a small stored concept bias and bounded niche-quality adjustment prevent identical form scores across materially different niches. No visual was generated. Federal/common-law phrase review remains a separate gate. Дата: 2026-09-23 09:51:32.257179+00.
- **distinctiveness**: 9.30 (confidence 0.744). Unified Forge concept-depth score. Profile captures the concept form (technical map, diagnostic, system map, workflow, process or terminology); a small stored concept bias and bounded niche-quality adjustment prevent identical form scores across materially different niches. No visual was generated. Federal/common-law phrase review remains a separate gate. Дата: 2026-09-23 09:51:32.257179+00.
- **giftability**: 7.32 (confidence 0.684). Unified Forge concept-depth score. Profile captures the concept form (technical map, diagnostic, system map, workflow, process or terminology); a small stored concept bias and bounded niche-quality adjustment prevent identical form scores across materially different niches. No visual was generated. Federal/common-law phrase review remains a separate gate. Дата: 2026-09-23 09:51:32.257179+00.
- **insider_resonance**: 9.30 (confidence 0.759). Unified Forge concept-depth score. Profile captures the concept form (technical map, diagnostic, system map, workflow, process or terminology); a small stored concept bias and bounded niche-quality adjustment prevent identical form scores across materially different niches. No visual was generated. Federal/common-law phrase review remains a separate gate. Дата: 2026-09-23 09:51:32.257179+00.
- **ip_safety**: 9.00 (confidence 0.550). Unified Forge concept-depth score. Profile captures the concept form (technical map, diagnostic, system map, workflow, process or terminology); a small stored concept bias and bounded niche-quality adjustment prevent identical form scores across materially different niches. No visual was generated. Federal/common-law phrase review remains a separate gate. Дата: 2026-09-23 09:51:32.257179+00.
- **niche_fit**: 9.42 (confidence 0.766). Unified Forge concept-depth score. Profile captures the concept form (technical map, diagnostic, system map, workflow, process or terminology); a small stored concept bias and bounded niche-quality adjustment prevent identical form scores across materially different niches. No visual was generated. Federal/common-law phrase review remains a separate gate. Дата: 2026-09-23 09:51:32.257179+00.
- **visual_potential**: 9.90 (confidence 0.781). Unified Forge concept-depth score. Profile captures the concept form (technical map, diagnostic, system map, workflow, process or terminology); a small stored concept bias and bounded niche-quality adjustment prevent identical form scores across materially different niches. No visual was generated. Federal/common-law phrase review remains a separate gate. Дата: 2026-09-23 09:51:32.257179+00.

## 47. Wastewater Operator
Ключ: `wastewater_operator` · ID: `a4090b28-a22b-4929-ad08-30e1d5f20c4b`

**Статус БД:** scored · **балл:** 77.45 · **confidence:** 75.72 · **coverage:** 100.00
**Аудитория:** Municipal wastewater treatment operators
**Категория:** occupational_identity
**Исследовательская аргументация:** Legacy Town Label occupational niche carried forward for re-evaluation under the new niche-first scoring engine. Existing artwork quality does not determine niche status.
**Создано / обновлено:** 2026-09-23 06:11:01.997287+00 / 2026-09-23 09:44:55.053118+00

### Компоненты оценки ниши

- **channel_breadth**: 7.00 (confidence 0.600). Legacy Forge/Town Label niche rescored under the unified Forge rubric using current 2025-35 BLS data plus the 2026-09-21/22 marketplace and IP research already stored in merch.research_notes. Existing visual rejection does not count as niche rejection. Дата: 2026-09-23 09:44:55.053118+00.
- **competition_opportunity**: 8.00 (confidence 0.780). Legacy Forge/Town Label niche rescored under the unified Forge rubric using current 2025-35 BLS data plus the 2026-09-21/22 marketplace and IP research already stored in merch.research_notes. Existing visual rejection does not count as niche rejection. Дата: 2026-09-23 09:44:55.053118+00.
- **concept_depth**: 9.00 (confidence 0.780). Legacy Forge/Town Label niche rescored under the unified Forge rubric using current 2025-35 BLS data plus the 2026-09-21/22 marketplace and IP research already stored in merch.research_notes. Existing visual rejection does not count as niche rejection. Дата: 2026-09-23 09:44:55.053118+00.
- **demand_evidence**: 6.50 (confidence 0.900). Legacy Forge/Town Label niche rescored under the unified Forge rubric using current 2025-35 BLS data plus the 2026-09-21/22 marketplace and IP research already stored in merch.research_notes. Existing visual rejection does not count as niche rejection. Дата: 2026-09-23 09:44:55.053118+00.
- **founder_edge**: 2.00 (confidence 0.400). Legacy Forge/Town Label niche rescored under the unified Forge rubric using current 2025-35 BLS data plus the 2026-09-21/22 marketplace and IP research already stored in merch.research_notes. Existing visual rejection does not count as niche rejection. Дата: 2026-09-23 09:44:55.053118+00.
- **identity_intensity**: 8.50 (confidence 0.740). Legacy Forge/Town Label niche rescored under the unified Forge rubric using current 2025-35 BLS data plus the 2026-09-21/22 marketplace and IP research already stored in merch.research_notes. Existing visual rejection does not count as niche rejection. Дата: 2026-09-23 09:44:55.053118+00.
- **legal_safety**: 8.50 (confidence 0.720). Legacy Forge/Town Label niche rescored under the unified Forge rubric using current 2025-35 BLS data plus the 2026-09-21/22 marketplace and IP research already stored in merch.research_notes. Existing visual rejection does not count as niche rejection. Дата: 2026-09-23 09:44:55.053118+00.
- **purchase_motivation**: 7.50 (confidence 0.660). Legacy Forge/Town Label niche rescored under the unified Forge rubric using current 2025-35 BLS data plus the 2026-09-21/22 marketplace and IP research already stored in merch.research_notes. Existing visual rejection does not count as niche rejection. Дата: 2026-09-23 09:44:55.053118+00.
- **repeatability**: 8.00 (confidence 0.660). Legacy Forge/Town Label niche rescored under the unified Forge rubric using current 2025-35 BLS data plus the 2026-09-21/22 marketplace and IP research already stored in merch.research_notes. Existing visual rejection does not count as niche rejection. Дата: 2026-09-23 09:44:55.053118+00.
- **visual_language**: 9.00 (confidence 0.800). Legacy Forge/Town Label niche rescored under the unified Forge rubric using current 2025-35 BLS data plus the 2026-09-21/22 marketplace and IP research already stored in merch.research_notes. Existing visual rejection does not count as niche rejection. Дата: 2026-09-23 09:44:55.053118+00.

### Концепции (1)

#### Wastewater — treatment operations
`wastewater_treatment_operations` · ID `47376c56-bebb-485f-9efc-697e5a5ff9d3`

**Интерпретация:** Исследовательский кандидат; одобрение владельца не зафиксировано
**Статус БД:** scored · **балл:** 87.80 · **confidence:** 73.01 · **coverage:** 100.00
**Текст / хук:** treatment-operations / process-monitoring schematic
**Идея:** Wastewater Operator professional process-control identity graphic. Production v3 uses TREATMENT OPERATIONS plus SAMPLE / MONITOR / ADJUST / LOG and PLANT • PROCESS • COMPLIANCE. PROCESS CONTROL was removed after an exact live federal mark surfaced in unrelated machinery/control classes. The concept is based on wastewater operator tasks and avoids sewage jokes, generic retro badges, certification seals, copied SCADA/HMI screens, and educational treatment-process diagrams.
**Покупатель:** Municipal wastewater treatment operators
**Причина покупки:** trade identity and public-infrastructure pride; insider recognition without sewage-joke cliché
**Отличие:** narrow apparel results are relatively small and humor-heavy; technical process angle appears less represented
**Создано / обновлено:** 2026-09-23 06:11:42.741293+00 / 2026-09-23 10:17:05.900325+00

Компоненты оценки:
- **buyer_desire**: 8.27 (confidence 0.729). Unified Forge concept-depth score. Profile captures the concept form (technical map, diagnostic, system map, workflow, process or terminology); a small stored concept bias and bounded niche-quality adjustment prevent identical form scores across materially different niches. No visual was generated. Federal/common-law phrase review remains a separate gate. Дата: 2026-09-23 09:51:32.257179+00.
- **clarity_at_glance**: 8.40 (confidence 0.722). Unified Forge concept-depth score. Profile captures the concept form (technical map, diagnostic, system map, workflow, process or terminology); a small stored concept bias and bounded niche-quality adjustment prevent identical form scores across materially different niches. No visual was generated. Federal/common-law phrase review remains a separate gate. Дата: 2026-09-23 09:51:32.257179+00.
- **distinctiveness**: 9.00 (confidence 0.737). Unified Forge concept-depth score. Profile captures the concept form (technical map, diagnostic, system map, workflow, process or terminology); a small stored concept bias and bounded niche-quality adjustment prevent identical form scores across materially different niches. No visual was generated. Federal/common-law phrase review remains a separate gate. Дата: 2026-09-23 09:51:32.257179+00.
- **giftability**: 7.67 (confidence 0.692). Unified Forge concept-depth score. Profile captures the concept form (technical map, diagnostic, system map, workflow, process or terminology); a small stored concept bias and bounded niche-quality adjustment prevent identical form scores across materially different niches. No visual was generated. Federal/common-law phrase review remains a separate gate. Дата: 2026-09-23 09:51:32.257179+00.
- **insider_resonance**: 9.10 (confidence 0.752). Unified Forge concept-depth score. Profile captures the concept form (technical map, diagnostic, system map, workflow, process or terminology); a small stored concept bias and bounded niche-quality adjustment prevent identical form scores across materially different niches. No visual was generated. Federal/common-law phrase review remains a separate gate. Дата: 2026-09-23 09:51:32.257179+00.
- **ip_safety**: 8.90 (confidence 0.550). Unified Forge concept-depth score. Profile captures the concept form (technical map, diagnostic, system map, workflow, process or terminology); a small stored concept bias and bounded niche-quality adjustment prevent identical form scores across materially different niches. No visual was generated. Federal/common-law phrase review remains a separate gate. Дата: 2026-09-23 09:51:32.257179+00.
- **niche_fit**: 9.37 (confidence 0.767). Unified Forge concept-depth score. Profile captures the concept form (technical map, diagnostic, system map, workflow, process or terminology); a small stored concept bias and bounded niche-quality adjustment prevent identical form scores across materially different niches. No visual was generated. Federal/common-law phrase review remains a separate gate. Дата: 2026-09-23 09:51:32.257179+00.
- **visual_potential**: 9.40 (confidence 0.767). Unified Forge concept-depth score. Profile captures the concept form (technical map, diagnostic, system map, workflow, process or terminology); a small stored concept bias and bounded niche-quality adjustment prevent identical form scores across materially different niches. No visual was generated. Federal/common-law phrase review remains a separate gate. Дата: 2026-09-23 09:51:32.257179+00.

## 48. Wind Turbine Service Technician
Ключ: `wind_turbine_service_technician` · ID: `3d4024a3-2aaf-4f9c-ad2c-bc5032f01dde`

**Статус БД:** scored · **балл:** 78.35 · **confidence:** 79.48 · **coverage:** 100.00
**Аудитория:** Wind turbine service technicians / windtechs
**Категория:** occupational_identity
**Исследовательская аргументация:** Legacy Town Label occupational niche carried forward for re-evaluation under the new niche-first scoring engine. Existing artwork quality does not determine niche status.
**Создано / обновлено:** 2026-09-23 06:11:01.997287+00 / 2026-09-23 10:03:30.159451+00

### Компоненты оценки ниши

- **channel_breadth**: 8.00 (confidence 0.660). Legacy Forge/Town Label niche rescored under the unified Forge rubric using current 2025-35 BLS data plus the 2026-09-21/22 marketplace and IP research already stored in merch.research_notes. Existing visual rejection does not count as niche rejection. Дата: 2026-09-23 09:44:55.053118+00.
- **competition_opportunity**: 5.50 (confidence 0.780). Legacy Forge/Town Label niche rescored under the unified Forge rubric using current 2025-35 BLS data plus the 2026-09-21/22 marketplace and IP research already stored in merch.research_notes. Existing visual rejection does not count as niche rejection. Дата: 2026-09-23 09:44:55.053118+00.
- **concept_depth**: 9.50 (confidence 0.820). Legacy Forge/Town Label niche rescored under the unified Forge rubric using current 2025-35 BLS data plus the 2026-09-21/22 marketplace and IP research already stored in merch.research_notes. Existing visual rejection does not count as niche rejection. Дата: 2026-09-23 09:44:55.053118+00.
- **demand_evidence**: 7.00 (confidence 0.920). Legacy Forge/Town Label niche rescored under the unified Forge rubric using current 2025-35 BLS data plus the 2026-09-21/22 marketplace and IP research already stored in merch.research_notes. Existing visual rejection does not count as niche rejection. Дата: 2026-09-23 09:44:55.053118+00.
- **founder_edge**: 2.00 (confidence 0.400). Legacy Forge/Town Label niche rescored under the unified Forge rubric using current 2025-35 BLS data plus the 2026-09-21/22 marketplace and IP research already stored in merch.research_notes. Existing visual rejection does not count as niche rejection. Дата: 2026-09-23 09:44:55.053118+00.
- **identity_intensity**: 9.00 (confidence 0.800). Legacy Forge/Town Label niche rescored under the unified Forge rubric using current 2025-35 BLS data plus the 2026-09-21/22 marketplace and IP research already stored in merch.research_notes. Existing visual rejection does not count as niche rejection. Дата: 2026-09-23 09:44:55.053118+00.
- **legal_safety**: 8.50 (confidence 0.720). Legacy Forge/Town Label niche rescored under the unified Forge rubric using current 2025-35 BLS data plus the 2026-09-21/22 marketplace and IP research already stored in merch.research_notes. Existing visual rejection does not count as niche rejection. Дата: 2026-09-23 09:44:55.053118+00.
- **purchase_motivation**: 8.00 (confidence 0.720). Legacy Forge/Town Label niche rescored under the unified Forge rubric using current 2025-35 BLS data plus the 2026-09-21/22 marketplace and IP research already stored in merch.research_notes. Existing visual rejection does not count as niche rejection. Дата: 2026-09-23 09:44:55.053118+00.
- **repeatability**: 8.50 (confidence 0.720). Legacy Forge/Town Label niche rescored under the unified Forge rubric using current 2025-35 BLS data plus the 2026-09-21/22 marketplace and IP research already stored in merch.research_notes. Existing visual rejection does not count as niche rejection. Дата: 2026-09-23 09:44:55.053118+00.
- **visual_language**: 10.00 (confidence 0.860). Legacy Forge/Town Label niche rescored under the unified Forge rubric using current 2025-35 BLS data plus the 2026-09-21/22 marketplace and IP research already stored in merch.research_notes. Existing visual rejection does not count as niche rejection. Дата: 2026-09-23 09:44:55.053118+00.

### Концепции (7)

#### Wind — field service loop
`wind_climb_inspect_service_return` · ID `eaf9bb49-52b6-42ad-8d44-c720514a4f40`

**Интерпретация:** Исследовательский кандидат; одобрение владельца не зафиксировано
**Статус БД:** scored · **балл:** 84.90 · **confidence:** 67.17 · **coverage:** 100.00
**Текст / хук:** CLIMB • INSPECT • SERVICE • RETURN
**Идея:** Wind — field service loop. Core hook: CLIMB • INSPECT • SERVICE • RETURN. Wind-turbine inspection, troubleshooting and multi-system field service. Execution must stay original and descriptive; avoid employer, OEM, certification-body, association and proprietary-interface branding.
**Покупатель:** Wind turbine service technicians
**Причина покупки:** Identity purchase for wind turbine service technicians who recognize the real workflow/systems language.
**Отличие:** Insider technical workflow direction intended to avoid generic profession-title, retro-badge, skull, flag, coffee and parody templates.
**Визуальное направление:** Field-service workflow with tower/nacelle/tool motifs; no safety-procedure detail.
**Создано / обновлено:** 2026-09-23 09:48:50.541446+00 / 2026-09-23 09:55:40.114238+00

Компоненты оценки:
- **buyer_desire**: 8.11 (confidence 0.660). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **clarity_at_glance**: 9.13 (confidence 0.660). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **distinctiveness**: 8.30 (confidence 0.660). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **giftability**: 8.03 (confidence 0.660). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **insider_resonance**: 8.75 (confidence 0.690). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **ip_safety**: 9.00 (confidence 0.660). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **niche_fit**: 9.21 (confidence 0.690). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **visual_potential**: 8.35 (confidence 0.690). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.

#### Wind — fault to field repair
`wind_fault_code_field_repair` · ID `8be0e46f-d026-43d8-a20e-18d1dbb9f372`

**Интерпретация:** Исследовательский кандидат; одобрение владельца не зафиксировано
**Статус БД:** scored · **балл:** 88.61 · **confidence:** 69.17 · **coverage:** 100.00
**Текст / хук:** ALERT → DIAGNOSE → FIELD → VERIFY
**Идея:** Wind — fault to field repair. Core hook: ALERT → DIAGNOSE → FIELD → VERIFY. Wind-turbine inspection, troubleshooting and multi-system field service. Execution must stay original and descriptive; avoid employer, OEM, certification-body, association and proprietary-interface branding.
**Покупатель:** Wind turbine service technicians
**Причина покупки:** Identity purchase for wind turbine service technicians who recognize the real workflow/systems language.
**Отличие:** Insider technical diagnostic direction intended to avoid generic profession-title, retro-badge, skull, flag, coffee and parody templates.
**Визуальное направление:** Remote-alert to onsite verification workflow; generic and not a copied SCADA interface.
**Создано / обновлено:** 2026-09-23 09:48:50.541446+00 / 2026-09-23 09:55:40.114238+00

Компоненты оценки:
- **buyer_desire**: 8.61 (confidence 0.680). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **clarity_at_glance**: 8.57 (confidence 0.680). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **distinctiveness**: 9.00 (confidence 0.680). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **giftability**: 7.87 (confidence 0.680). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **insider_resonance**: 9.40 (confidence 0.710). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **ip_safety**: 8.70 (confidence 0.680). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **niche_fit**: 9.41 (confidence 0.710). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **visual_potential**: 8.90 (confidence 0.710). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.

#### Wind — gearbox / generator / converter
`wind_gearbox_generator_converter` · ID `28c5d148-76e1-45d9-bceb-ed7d46b49e89`

**Интерпретация:** Исследовательский кандидат; одобрение владельца не зафиксировано
**Статус БД:** scored · **балл:** 88.03 · **confidence:** 69.17 · **coverage:** 100.00
**Текст / хук:** GEARBOX • GENERATOR • CONVERTER
**Идея:** Wind — gearbox / generator / converter. Core hook: GEARBOX • GENERATOR • CONVERTER. Wind-turbine inspection, troubleshooting and multi-system field service. Execution must stay original and descriptive; avoid employer, OEM, certification-body, association and proprietary-interface branding.
**Покупатель:** Wind turbine service technicians
**Причина покупки:** Identity purchase for wind turbine service technicians who recognize the real workflow/systems language.
**Отличие:** Insider technical system map direction intended to avoid generic profession-title, retro-badge, skull, flag, coffee and parody templates.
**Визуальное направление:** Powertrain/electrical system map within a simplified nacelle outline.
**Создано / обновлено:** 2026-09-23 09:48:50.541446+00 / 2026-09-23 09:55:40.114238+00

Компоненты оценки:
- **buyer_desire**: 8.41 (confidence 0.680). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **clarity_at_glance**: 8.17 (confidence 0.680). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **distinctiveness**: 9.00 (confidence 0.680). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **giftability**: 7.57 (confidence 0.680). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **insider_resonance**: 9.10 (confidence 0.710). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **ip_safety**: 8.80 (confidence 0.680). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **niche_fit**: 9.31 (confidence 0.710). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **visual_potential**: 9.60 (confidence 0.710). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.

#### Wind — nacelle systems map
`wind_nacelle_systems_map` · ID `26007688-d037-45b0-89ea-b8fd22a183ac`

**Интерпретация:** Исследовательский кандидат; одобрение владельца не зафиксировано
**Статус БД:** scored · **балл:** 88.64 · **confidence:** 69.17 · **coverage:** 100.00
**Текст / хук:** NACELLE • DRIVE • CONTROL
**Идея:** Wind — nacelle systems map. Core hook: NACELLE • DRIVE • CONTROL. Wind-turbine inspection, troubleshooting and multi-system field service. Execution must stay original and descriptive; avoid employer, OEM, certification-body, association and proprietary-interface branding.
**Покупатель:** Wind turbine service technicians
**Причина покупки:** Identity purchase for wind turbine service technicians who recognize the real workflow/systems language.
**Отличие:** Insider technical system map direction intended to avoid generic profession-title, retro-badge, skull, flag, coffee and parody templates.
**Визуальное направление:** Original nacelle system map emphasizing serviceable mechanical/electrical/control subsystems rather than a scenic turbine silhouette.
**Создано / обновлено:** 2026-09-23 09:48:50.541446+00 / 2026-09-23 09:57:07.855981+00

Компоненты оценки:
- **buyer_desire**: 8.51 (confidence 0.680). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **clarity_at_glance**: 8.20 (confidence 0.680). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **distinctiveness**: 9.10 (confidence 0.680). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **giftability**: 7.60 (confidence 0.680). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **insider_resonance**: 9.15 (confidence 0.710). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **ip_safety**: 8.80 (confidence 0.680). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **niche_fit**: 9.31 (confidence 0.710). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **visual_potential**: 9.65 (confidence 0.710). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.

#### Wind — pitch / yaw / drive / control
`wind_pitch_yaw_drive_control` · ID `a771c757-9b5d-450c-b551-a6656da08919`

**Интерпретация:** Исследовательский кандидат; одобрение владельца не зафиксировано
**Статус БД:** scored · **балл:** 87.47 · **confidence:** 67.17 · **coverage:** 100.00
**Текст / хук:** PITCH • YAW • DRIVE • CONTROL
**Идея:** Wind — pitch / yaw / drive / control. Core hook: PITCH • YAW • DRIVE • CONTROL. Wind-turbine inspection, troubleshooting and multi-system field service. Execution must stay original and descriptive; avoid employer, OEM, certification-body, association and proprietary-interface branding.
**Покупатель:** Wind turbine service technicians
**Причина покупки:** Identity purchase for wind turbine service technicians who recognize the real workflow/systems language.
**Отличие:** Insider technical terminology direction intended to avoid generic profession-title, retro-badge, skull, flag, coffee and parody templates.
**Визуальное направление:** Four turbine subsystems rendered in an original technical stack.
**Создано / обновлено:** 2026-09-23 09:48:50.541446+00 / 2026-09-23 09:55:40.114238+00

Компоненты оценки:
- **buyer_desire**: 8.11 (confidence 0.660). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **clarity_at_glance**: 9.30 (confidence 0.660). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **distinctiveness**: 8.60 (confidence 0.660). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **giftability**: 8.20 (confidence 0.660). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **insider_resonance**: 9.55 (confidence 0.690). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **ip_safety**: 8.80 (confidence 0.660). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **niche_fit**: 9.41 (confidence 0.690). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **visual_potential**: 8.55 (confidence 0.690). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.

#### Wind — SCADA to field verification
`wind_scada_to_field_verify` · ID `b0a333a3-1253-4b02-9f8b-10ae41dc5571`

**Интерпретация:** Исследовательский кандидат; одобрение владельца не зафиксировано
**Статус БД:** scored · **балл:** 87.41 · **confidence:** 68.17 · **coverage:** 100.00
**Текст / хук:** SCADA → FIELD → VERIFY
**Идея:** Wind — SCADA to field verification. Core hook: SCADA → FIELD → VERIFY. Wind-turbine inspection, troubleshooting and multi-system field service. Execution must stay original and descriptive; avoid employer, OEM, certification-body, association and proprietary-interface branding.
**Покупатель:** Wind turbine service technicians
**Причина покупки:** Identity purchase for wind turbine service technicians who recognize the real workflow/systems language.
**Отличие:** Insider technical technical map direction intended to avoid generic profession-title, retro-badge, skull, flag, coffee and parody templates.
**Визуальное направление:** High-level remote-monitoring-to-field-service concept using generic alert/data symbols; no proprietary screen.
**Создано / обновлено:** 2026-09-23 09:48:50.541446+00 / 2026-09-23 09:55:40.114238+00

Компоненты оценки:
- **buyer_desire**: 8.21 (confidence 0.670). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **clarity_at_glance**: 7.73 (confidence 0.670). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **distinctiveness**: 9.10 (confidence 0.670). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **giftability**: 7.43 (confidence 0.670). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **insider_resonance**: 9.25 (confidence 0.700). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **ip_safety**: 8.60 (confidence 0.670). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **niche_fit**: 9.31 (confidence 0.700). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.
- **visual_potential**: 9.55 (confidence 0.700). Provisional Forge concept-depth score. Derived from the concept archetype (technical map / system map / diagnostic / workflow / process / terminology), the fully scored niche prior, and current occupational terminology already stored in the candidate. This score measures research priority, not sales probability and not legal clearance. Дата: 2026-09-23 09:55:40.114238+00.

#### Wind — electrical / mechanical / hydraulic systems
`wind_systems_service` · ID `cbbd18e0-6e50-40f3-9159-268984600400`

**Интерпретация:** Исследовательский кандидат; одобрение владельца не зафиксировано
**Статус БД:** scored · **балл:** 89.81 · **confidence:** 74.21 · **coverage:** 100.00
**Текст / хук:** ELECTRICAL • MECHANICAL • HYDRAULIC | INSPECT • TEST • TROUBLESHOOT • REPAIR
**Идея:** Wind Turbine Service Technician professional technical-systems graphic using the full occupational title plus ELECTRICAL • MECHANICAL • HYDRAULIC and INSPECT • TEST • TROUBLESHOOT • REPAIR. Research proof A uses an abstract three-blade service schematic instead of retro sunset, cowboy, clean-energy slogan, or height joke treatments.
**Покупатель:** Wind turbine service technicians / windtechs
**Отличие:** Visible Wind Turbine Technician apparel is crowded with generic job-title, retro, cowboy, big-fan, height and joke treatments; technical service-system hierarchy is less represented.
**Создано / обновлено:** 2026-09-23 06:11:42.741293+00 / 2026-09-23 10:17:05.900325+00

Компоненты оценки:
- **buyer_desire**: 8.52 (confidence 0.739). Unified Forge concept-depth score. Profile captures the concept form (technical map, diagnostic, system map, workflow, process or terminology); a small stored concept bias and bounded niche-quality adjustment prevent identical form scores across materially different niches. No visual was generated. Federal/common-law phrase review remains a separate gate. Дата: 2026-09-23 09:51:32.257179+00.
- **clarity_at_glance**: 8.10 (confidence 0.716). Unified Forge concept-depth score. Profile captures the concept form (technical map, diagnostic, system map, workflow, process or terminology); a small stored concept bias and bounded niche-quality adjustment prevent identical form scores across materially different niches. No visual was generated. Federal/common-law phrase review remains a separate gate. Дата: 2026-09-23 09:51:32.257179+00.
- **distinctiveness**: 9.30 (confidence 0.754). Unified Forge concept-depth score. Profile captures the concept form (technical map, diagnostic, system map, workflow, process or terminology); a small stored concept bias and bounded niche-quality adjustment prevent identical form scores across materially different niches. No visual was generated. Federal/common-law phrase review remains a separate gate. Дата: 2026-09-23 09:51:32.257179+00.
- **giftability**: 7.52 (confidence 0.694). Unified Forge concept-depth score. Profile captures the concept form (technical map, diagnostic, system map, workflow, process or terminology); a small stored concept bias and bounded niche-quality adjustment prevent identical form scores across materially different niches. No visual was generated. Federal/common-law phrase review remains a separate gate. Дата: 2026-09-23 09:51:32.257179+00.
- **insider_resonance**: 9.30 (confidence 0.769). Unified Forge concept-depth score. Profile captures the concept form (technical map, diagnostic, system map, workflow, process or terminology); a small stored concept bias and bounded niche-quality adjustment prevent identical form scores across materially different niches. No visual was generated. Federal/common-law phrase review remains a separate gate. Дата: 2026-09-23 09:51:32.257179+00.
- **ip_safety**: 9.00 (confidence 0.550). Unified Forge concept-depth score. Profile captures the concept form (technical map, diagnostic, system map, workflow, process or terminology); a small stored concept bias and bounded niche-quality adjustment prevent identical form scores across materially different niches. No visual was generated. Federal/common-law phrase review remains a separate gate. Дата: 2026-09-23 09:51:32.257179+00.
- **niche_fit**: 9.62 (confidence 0.776). Unified Forge concept-depth score. Profile captures the concept form (technical map, diagnostic, system map, workflow, process or terminology); a small stored concept bias and bounded niche-quality adjustment prevent identical form scores across materially different niches. No visual was generated. Federal/common-law phrase review remains a separate gate. Дата: 2026-09-23 09:51:32.257179+00.
- **visual_potential**: 9.90 (confidence 0.791). Unified Forge concept-depth score. Profile captures the concept form (technical map, diagnostic, system map, workflow, process or terminology); a small stored concept bias and bounded niche-quality adjustment prevent identical form scores across materially different niches. No visual was generated. Federal/common-law phrase review remains a separate gate. Дата: 2026-09-23 09:51:32.257179+00.

