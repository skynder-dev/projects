# RevEng — состояние у Claude

## 2026-10-31, начало

- Пакет передачи 30.10 лежит в `MIGRATION/reveng/2026-10-30/` без изменений. Работа начата по просьбе владельца 31.10 («по остальным проектам что? стоим?»).
- Идея владельца 31.10: RevEng может искать и **конкурсы** (видео, ИИ-кино и т.п.): это реальная возможность с призом, сроком и правилами, «да не revenue, но реально», и одна работа идёт на много площадок.

### Карта (по пакету и по ПК, только чтение)
- Цель правок по пакету: `reveng/ResearchLocal` (C# WinForms-обёртка + Python-воркеры, строгий JSON с SHA256, без БД). Линии Node reference и G280/G281 overlay отдельно, не трогать. Целевая линия владельцем формально не закреплена (P0).
- На ПК: рабочая установка `D:\Projects\RevEng\Prototype\` (RevEngResearch.exe от 17.10, ResearchLocal от 16–17.10), десятки резервных копий в `D:\Projects\RevEng\Backups\`. Исходники пакета от 28.10 новее установленного.
- Источники сейчас жёстко заданы (`SOURCES` в `reveng_local_research.py`: wordpress.org, StackExchange, HN Algolia, npm), официальные страницы через `official_observations`/`official_html` (нужен bs4, его нет — 10 из 15 проверок возможностей падают с missing-bs4).
- Исполнитель модели выключен (`execution_disabled=true`, `FAILED_SEMANTIC_ATTRIBUTION`) — не трогать ради видимости.
- Сборка: `csc.exe /target:winexe /main:LocalEntry` по всем `*.cs`; проверки: `python -I -B reveng/tests/<suite>.py --source reveng/ResearchLocal` (и с `-O`). Hosted CI не запускался; в публичном реестре нет workflow.

### Куда встраивать «Конкурсы» (минимум изменений)
- Новая запись в `SOURCES` + ветка разбора в `source_context.parse_api`, вид строки `official_contest_listing` (не в `PROBLEM_REPORT_KINDS`: конкурс — это условия, а не боль покупателя).
- Правила конкурса со страницы организатора через `official_observations`/`official_html` по образцу `direct_alternatives.py` (`TASKS` + regex `rules`): срок, приз, взнос, кто может участвовать, обязательные инструменты, длительность/формат, эксклюзивность/премьера, ссылка. Приз/взнос как `price_experiments` (`proposed_unverified`), срок — отдельная заявленная дата.
- Категория в `CATEGORIES`, `saved_analysis_context.PUBLIC_HOSTS/KINDS`, отображение в `RenderCard` и `EvidenceComparison.Describe`, файлы в allowlist `research_export`; обновить `RESEARCH_LOCAL_SOURCE_MANIFEST.json`.
- Не добавлять конкурсы в общий рейтинг автоматически (прецедент в 02:424).

### Ограничения передачи
- Без новых расходов, модельных вызовов, установки зависимостей (bs4!), контактов, публикаций — без согласия владельца.
- Ручной поиск ассистента не выдавать за автономный результат RevEng.

### Первый нативный прогон (31.10, GitHub Windows, `reveng-windows.yml`)
- Исходники ResearchLocal 28.10 перенесены в `reveng/ResearchLocal` и `reveng/tests` байт в байт (манифест 122/122), `reveng/.gitattributes` держит байты на любой ОС.
- **Всё приложение компилируется** (`csc` .NET Framework 4, 30 файлов → wrapper.exe 377 КБ) и **все 5 нативных C#-проб проходят** (TestOutcome, TestPriceExperimentPresentation, TestOwnerPreferencePresentation, TestPortableRuntimeDrain, TestOperationOutcome) — раньше это было NOT_RUN.
- Python-проверки на Windows (3.11, обычный и -O): проходят 4 из 12 (capability, price_ui_contract, saved_analysis_context, task_routing); падают 8 (answer_cache_integrity, collection_integrity, hypothesis_contract, identity_portable, owner_preference_overlay, price_cache_integrity, price_experiment_projection, researchlocal_offline). На Linux (3.13) те же наборы проходят, кроме одного хеша AST, зависящего от версии Python. Значит, есть именно Windows-расхождения; их надо разобрать до встраивания «Конкурсов», потому что программа работает на Windows у владельца.

### Windows зелёный (31.10, позже в тот же вечер)
- Из 8 падений 5 были от моей настройки CI (принудительный `REVENG_OFFLINE_REPLAY=1` ломал проверки, которые подменяют `read_http`; одной проверке PowerShell передавал аргумент не одним списком).
- Настоящая ошибка Windows: `source_ledger.verify_portable` и `research_chain` сравнивали развёрнутый путь (`resolve()`) с неразвёрнутой временной папкой; на Windows временная папка бывает в коротком виде 8.3 (`RUNNER~1`), и каждый проверенный экспорт падал с «Ledger input missing/unsafe in export». Исправлено: `root=Path(folder).resolve()`; записи манифеста обновлены (изменение `+windows_resolved_temp_root_2026-10-31`).
- Итог `reveng-windows.yml`: приложение компилируется, 5/5 нативных проб, 11/11 Python-наборов в обычном и `-O` режимах (12-й требует `.ci`-обвязку, которой нет в пакете). Это проверено на GitHub Windows; на ПК владельца не установлено, владельцем не принято.

### «Конкурсы» (31.10–01.11)
- `reveng/ResearchLocal/contest_terms.py`: страницы организаторов читаются тем же ограниченным транспортом приложения (HTTPS, robots.txt, без переходов по редиректам, бюджет запросов), опечатанный кэш, без HTTP в офлайне. Условия только цитатами (до 14 слов): заявленный срок (не дата наблюдения), приз и взнос как `proposed_unverified`, длительность, обязательный инструмент, кто может участвовать, эксклюзивность, формат; «одна работа — несколько конкурсов» (пересечение длительности, без конфликта инструментов, с пометкой проверить эксклюзивность). Вне кандидатов и общего рейтинга (`automatic_admission=False`).
- Личность страницы: объявленный canonical/og:url должен совпасть; если не объявлен — точный HTTPS-адрес без редиректов (`source_identity`); страницы-заглушки отказа — отклоняются.
- `reveng/tests/test_contest_terms.py`: 9 офлайн-контрактов; зелёные на Linux и Windows (обычный и -O).
- Живой прогон `reveng-contests.yml` (GitHub, вручную) 01.11: AI Film Award 2027 — срок 2026-11-20, $1 000 000, 5–7 мин, ≥70% Seedance, весь мир, неисключительная лицензия, 16:9; Chroma Awards S2 — срок 2027-01-07, $190 000 призовых; WAIFF на FilmFreeway — 403 (закрыто для роботов, честно «недоступно»).
- Семена — ручной поиск ассистента 31.10, не автономное открытие RevEng. Дальше: источник-агрегатор (aifilmcontests.com) как вторичный список лидов → официальные страницы; показ в окне программы; установка на ПК (нужен bs4 — с согласия владельца).

### План
1. ~~Windows CI в GitHub~~ — сделано, зелёное.
2. «Конкурсы» внутри ResearchLocal (см. выше), с проверками.
3. Установка рядом со старой на ПК (старая не трогается), после согласия владельца.
