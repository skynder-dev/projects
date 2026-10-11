# MediaEngine: реестр решений и доказательств
Дата сверки: 2026-10-10. Основной контракт: CLAUDE_MASTER_CONTRACT_RU.md.

## Принятая авторитетная база
- Windows stable MediaEngine 3.12.42, рабочее пространство D:\Archivist.
- Принят MEDENG_AUTO_EDIT_V52_VIDEO_QUALITY_SIDECAR_RC1, слот v52-rc1, local 251/251 + Windows 6/6 = 257/257 PASS; результат от 2026-10-03.
- V52 ZIP SHA 6f6d4634a5edd650713b1fd758b620d2440958006822537ca0fb5d042364e17c.
- V52 acceptance относится к sidecar, а не к единому пользовательскому приложению P11.
- Stable, V52 и release 054 неизменны. Не выпускать V53/055 без доказанной новой способности и сознательного release gate.

## Свежайшая фактическая правка 2026-10-08
- Supabase проект media-business-projects, public.project_work_log 6460, 2026-10-08 19:06:27 UTC, и public.project_current_state на 2026-10-08 19:06:27 UTC.
- Windows Remote Lab agent 1.1.168; command 1214, report 1264 PASS.
- ИСПРАВЛЕННЫЙ R2 P11 FolderToReel, FAST_LOCAL semantic=required, 14926.mp4 входной SHA 9fa73a898c2297d87ee406237dc4c22d4b1f282926935893c327738c423c5f40.
- Желаемый 30s, фактический 29.97s, 6 сегментов, 1 camera-drop trim. Реальный reel MP4 8644722 bytes SHA 1a2605045d70de72577e8d55205ecf24efaf18c920e69390bacaba4c973c281f.
- Result JSON SHA b6873fce5db466b71f2285bb503e50177d4754966ce0a01756219efe037b3522.
- В proof исправлено (R1) отсутствующее technical_prominence: .50*eventness + .35*novelty + .15*quality; (R2) устранён искусственный top-3 обрезчик при уже bounded max_candidates=8. R2 orchestrator SHA 5c45fd8e3c86eda55d6f8a663ec723c823ef63f4b799e31022acc65f090ae99d.
- Реальный Windows semantic runtime PASS. **Native GUI EXE НЕ запускался в этом proof**, original P11_FolderToReel_Proof_002 байты не получали PASS. Не подменять.
- Source media untouched; pipeline_network_request_performed=false; удалённый транспорт использовал сеть; V52, stable, 054 не менялись.
- FAST_LOCAL model SHA 844d1a46ab18acf50c989e541b12fe3b6dc7f8d6004725b4e992d142788e0600; hook 2b15303eba5b02b7f949cb560e58b2dbee09ff4576e21ad4b25b2d3111b02d5c; adapter d7ef56b5b67e90179cecca366206eddd3b5ae4222ed4bc2f145a8b3f755eff36; validator 00e14d0d69b7f06cb5ef0841bee6c12809c6950a4ea3a677db9f7f715a107a22.

## Былые проблемы, не повторять
- Слепой двухклиповый benchmark 14926/14176 был открыт до R2. Второе видео 14176 и claim 2/2 отдельно не считать закрытыми.
- 2026-10-03 FULL_LIFECYCLE 23/23 PASS только с semantic=off, потому что exact FAST_LOCAL тогда не был исполнен. В ходе него нашли preset propagation bug: job просил Social HD, render hard-code 16:9. Shadow V3 его исправил. Без новой native проверки не смешивать.
- V25 standalone реальный auto-edit доказан, но его нельзя выдавать за интеграцию Windows UI.
- Попытки использовать GoDog Relay были заблокированы по безопасности, затем появилась легитимная ограниченная операция Remote Lab. Не обходить safety gate.
- 2026-10-07 исходный Proof_002 failed KeyError technical_prominence; фикс является bounded proof-only, не улучшением принятой V52.

## Доказанные shadow-контракты P11 (не native UI)
- INPUT: damaged/duplicate/unsupported skip, all-invalid fail closed, source untouched.
- Setup: visible only Length/Format/Sound, adaptive 9.28s source -> 5s default Social HD/Auto; semantic hidden required.
- Presets: один рендер за запрос, Horizontal 960x540, Vertical 540x960, Social HD 1080x1920, 1920x1080 будущая опция, не default.
- Montage sequence V4, pacing V1, audio coherence V2, camera-drop post-selection.
- Job state: atomic / crash resume / cancel / DONE idempotent.
- Review: variant reuse cache, immutable Revision 001+, Accept/Revert pointer only, accepted not auto-replaced.
- Export: one clean MP4 for user; no overwrite; repeated export no-op; source is verified Accepted revision.
- Project Home: Draft/Review/Ready/Attention, management metadata, verified open/reveal/copy.
- Closed in isolated local semantic-OFF chain: Import -> Setup -> Start -> Render -> Review -> Accept -> Export -> Completion 23/23.
- Все эти слои требуют нативной связки, а не нового shadow showcase.

## Ключевые исходные файлы
- /Media Engine Library: MEDENG_AUTO_EDIT_V52_CHECKPOINT_FINAL.json, MEDENG_AUTO_EDIT_V52_ACCEPTANCE_FINAL.json, MEDENG_P11_RELEASE_READINESS_CLOSURE_AUDIT_V1.json (старее R2).
- /Media Engine Library: P11_FolderToReel_Proof_002.zip и R1/RC2 runtime corrections.
- /Media Engine Library: P11_14176_Proof_002.zip, пользовательские videos 14926.mp4 / 14176.mp4 при наличии разрешения и private transfer.
- В публичном GitHub исходное дерево MediaEngine НЕ найдено на 2026-10-10. Этот репозиторий прежде содержал forge, reveng, social, MIGRATION. Настоящий исходный код нужно безопасно получить с D:\Archivist. Не переносить чужие media/secrets.

## Что остаётся USER GATE
- Подтверждение доступного и проверенного полного source tree / Windows установленного runtime и точного способа доступа.
- Нативный GUI workflow, включая импорт и review, на Windows еще не принят.
- Пользовательская оценка качества montage и UX (не заменяется хэшами).
- Деньги / публикация / изменение аккаунтов / выгрузка приватных файлов требуют явного согласия.

Для следующих работ без вопросов допустимы только обратимые code/docs/tests/CI на изолированной ветке при наличии исходников. После работы обновляй этот реестр на основании свежих первичных доказательств, не общих отчётов.
## Сверка Claude 2026-10-11 (первичные доказательства)
- Исходники найдены на ПК владельца и положены в git как базовый коммит `2cde3c7` (без изменений):
  `mediaengine/app` = 3.12.42 (43/43 файла = релиз-zip `58122c3a…`), `mediaengine/sidecar/auto_edit_v52-rc1` (96/96 по манифесту),
  `mediaengine/engine/p11_r2` (orchestrator `5c45fd8e…`, тот, что прошёл command 1214). Веса модели, видео и локальные конфиги не в git.
- Shadow-модули P11 UX (job/revision/export/home/first-run) на ПК отсутствуют; их функции заново сделаны внутри приложения.
- Кандидат 3.13.0-rc1: страница Auto Edit в существующем приложении поверх движка R3 (R2 + пресет, прогресс, исключения,
  таймлайн сегментов; модули рантайма байт-в-байт как в R2). Windows CI (GitHub runner, не ПК владельца) run 38112423526:
  R3 vs R2 28/28, ролики идентичны по байтам; E2E 7 видео 36/36, 2 видео 33/33, пакет стартует лаунчером без консоли,
  E2E на Python из пакета 33/33. Подробно: `mediaengine/STATUS.md`.
- Найдено и исправлено: (1) перенос строк git на Windows менял SHA закреплённых файлов → `.gitattributes mediaengine/** -text`;
  (2) кандидат перезаписывал ярлык «Archivist» и делил порт 8765 → свой порт 8775, свой ярлык, свой архив;
  (3) короткий результат при нехватке материала теперь честно показывается в UI.
- Не доказано: semantic=required из GUI на ПК владельца, качество выбора человеком, трим/перестановка в редакторе.

## Глубокий анализ Claude 2026-10-11
- Проверены приложение, Auto Edit, движок R3, лаунчер, пакет и CI. Stable 3.12.42, V52 и 054 не менялись.
- В stable 3.12.42 найдены ошибки с данными (исправлены только в кандидате): «Private forever» мог переместить оригинал
  пользователя; «Remove from Library» оставлял копию; дубликат мог импортироваться повторно; возраст файлов в watchdog
  неверен в часовых поясах UTC−x; фильтр смены сцен не срабатывал; недописанные файлы экспорта/конвертации.
- Движок R3: модули рантайма по-прежнему байт-в-байт как в R2; решения R3 = R2 на эталонном тесте. Задокументированные
  отличия оркестратора: пропуск файлов, которые анализ не может обработать (R2 падал целиком); библиотека моментов только из
  текущих файлов (R2 падал после удаления/замены/Private — воспроизведено); таймаут анализа растёт с длиной видео;
  ограниченный перебор (60 с из ≥30 моментов в R2 считался часами; ≤30 с — точно как R2); короткий ролик с
  `LIMITED_TOTAL_FOOTAGE` вместо ошибки; из двух окон одного источника с перекрытием >50 % берётся лучшее; повреждённый кэш
  пересобирается; Private-файлы не используются.
- Лаунчер/пакет: неверный `port.txt` останавливает запуск (не берёт 8765); пакет игнорирует чужой `ARCHIVIST_HOME`;
  второй запуск открывает уже работающий; второй сервер на том же порту не стартует; ярлык никогда не «Archivist»;
  VBS в UTF-16 (пути с кириллицей); Edge с обычным приоритетом; кнопка Quit; VC++ runtime внутри пакета;
  CI проверяет копию пакета в папке с кириллицей, артефакт не содержит данных CI.
- Не доказано: AI-режим из GUI на ПК владельца, качество выбора человеком, длинные/4K видео, синхронность звука на реальном материале.

