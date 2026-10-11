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