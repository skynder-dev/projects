# RevEng — карта файлов

Все пути относительно `reveng/` в репозитории `skynder-dev/projects` (ветка `main`). Ссылки для чтения: `https://raw.githubusercontent.com/skynder-dev/projects/main/reveng/<путь>`.
Подробная вводная: `HANDOFF_FOR_CHATGPT_RU.md` в этой папке. Таблица всех идей: `ideas_102.csv`.

## Документы (читать первыми)
| Файл | Что |
| --- | --- |
| `RESUME_STATE.md` | самое актуальное состояние и открытые решения |
| `ROADMAP.md` | карта на 10 часов, блоки A0–A9 со статусами |
| `app_overlay_g281/files/docs/REVA2_G281_SCAN2_REPORT_RU.md` | отчёт по сканам 1–3 по-русски |
| `app_overlay_g281/files/docs/REVA2_G281_GLOBAL_PATH.md` | описание модулей наложения (числа частично устарели, см. вводную) |
| `app_overlay_g281/README.md` | как применить наложение к оригинальному G280 |

## Наложение G281 (доработка вашего приложения)
| Что | Путь (внутри `app_overlay_g281/files/`) |
| --- | --- |
| Оценка v6 | `app/global_ranking_v6.js` |
| Ворота | `app/global_gates_v6.js` |
| Действительность скана | `app/global_scan_v6.js` |
| Протокол доказательств | `app/evidence_protocol_v6.js` |
| Защита расходов | `app/spend_guard_v6.js` |
| Экран «Global ranking» | `app/global_ranking.html`, `.css`, `global_ranking_page.js`, `global_ranking_view.js`, `app/data/g281_scan{1,2,3}_view.js` |
| Единственная правка G280 | `app/index.html` (ссылка в боковой панели) |
| Пакеты импорта в БД (с ROLLBACK) | `server/REVA2_G281_SCAN{1,2,3}_IMPORT.json`, `…_DRYRUN.sql`, `REVA2_G281_SOURCE_POLICY_SNAPSHOT.json` |
| Тесты | `diagnostics/tests/reva2_g281_*.mjs`, `test_reva2_g281_global_ranking_page.py`, `verify_reva2_g281_overlay.py` |
| Инструменты | `diagnostics/tools/` (сборщики пакетов, агрегатор, валидаторы, пробный SQL, манифест, `g281_local_schema/`) |
| Манифест файлов с SHA-256 | `docs/REVA2_G281_OVERLAY_MANIFEST.json` |
| Применение к G280 | `app_overlay_g281/apply_overlay.sh <папка G280> <новая папка>` |

## Данные сканов (`app_overlay_g281/files/samples/`)
| Папка | Что |
| --- | --- |
| `g281_scan1/` | скан 1: `01_raw.json` … `06_decision.json`, `deep/` (19 убито и 3 неясных), `deep2/` (повтор SAS-02, PHY-01), `deep2_unresolved/` (GAM-02, MED-03, EDU-03 без страниц), `verify/` (перечитка 66 цитат), `cases/`, `deep_status.json`, брифы |
| `g281_scan2/` | скан 2: `candidates/` (32), `deep/` (8), `verify/` (перечитка 95 цитат), `BRIEF.md`, `DEEP_BRIEF.md`, `aggregate.json`, `TIMES.json` |
| `g281_scan3/` | скан 3 (расширение): `candidates/` (30), `deep/` (4), `verify/` (76 цитат), брифы, `aggregate.json`, `TIMES.json` |

## Мой Node-движок (эталон, не продукт)
`src/` (движок: поиск, ворота, оценка, углублённая проверка, отчёт), `test/` (50 тестов), `config.json` (`allow_spend=false`), `config.example.json`, `vendor/` (модули G280 с хэшами), `manual/deep_screen_2026-10-10.md` (ручная проверка топ-3), `data_provisional/` (черновые данные первого скана), `fixtures/`. Ветка `results`: вывод первого живого прогона (`reveng/runs/…`). Workflow GitHub Actions: `.github/workflows/scan.yml` (платный запуск заблокирован `allow_spend=false`).

## Как проверить (Linux/WSL, Node ≥ 20, Python 3, Playwright + Chromium, PostgreSQL 16)
```
cd <дерево G281>                          # после apply_overlay.sh
for f in diagnostics/tests/reva2_g281_*.mjs; do node $f; done
python3 diagnostics/tests/test_reva2_g281_global_ranking_page.py
bash diagnostics/tools/dryrun_scan_import_g281.sh all     # ожидается 3,102,97,5,102
python3 diagnostics/tests/verify_reva2_g281_overlay.py
```
Старые Python-тесты G280 запускать только в копии дерева: они перезаписывают отчёты и скриншоты.
