# MediaEngine: acceptance matrix (must PASS, not just be promised)

| Test | Проверка | Required evidence |
|---|---|---|
| I01 | Настоящая чистая Windows установка/запуск без терминала | Запись процесса/лога Windows, package hash |
| I02 | Выбор папки с реальными MP4 (2 и 7 файлов), импорт и skip повреждённых | Source SHA до/после, manifest, GUI |
| I03 | Adaptive default при нехватке footage, Length/Format/Sound; семантика скрыта | Настоящий GUI + job request |
| I04 | Auto Edit реально запускает R2 semantic=required из GUI, не из вспомогательного CLI | Model hash, job identity, Result.json, GUI execution |
| I05 | 16:9 960x540, 9:16 540x960, Social HD 1080x1920 | ffprobe на каждом выбранном preset |
| I06 | Только один выбранный preset за запуск, без тройного рендера | File manifest/CPU time |
| I07 | Авто 15/30/60 и 5 при коротком материале, duration не подменена | Requested vs rendered timestamps |
| I08 | Sound: Source/Auto/Mute без скачка loudness | AAC / RMS / слышимое прослушивание |
| I09 | Выбор событий: semantic + технический tie-break, исключение камеры-дропа | candidate pool / intervals / boundary / human blind QA |
| I10 | Настоящий плеер и seek / candidate timeline / source links внутри GUI | Видео Windows user-interaction |
| I11 | Manual override, trim, exclude, reorder из GUI и новый результат | Дифф jobs, ffprobe, SHA старых неизменен |
| I12 | Make Variant preset/audio только использует analysis cache; изменение target selection cache | Cache hashes + timing |
| I13 | Accept/Revert pointer, immutable Revision и никакого auto-accept | Revision manifests and SHA |
| I14 | Stop/Cancel during segments, resume and recovery after crash | Atomic JOB_STATE, partial output not advertised DONE |
| I15 | Duplicate retry idempotent; input/model change isolated | Snapshot and SHA unchanged / new job |
| I16 | Export only Verified Accepted; filename Windows-safe; no overwrite | One MP4 in export root; exact SHA |
| I17 | Закрыть и открыть GUI, восстановить проект и последние решения | Windows restart proof |
| I18 | Неизменность originals, offline path, path safety, absent drive behavior | Original SHA, negative tests |
| I19 | Действительный offline/local render без Supabase/GoDog/облака | Run with network disabled and source logs |
| I20 | Комплект чистой поставки без Python/PowerShell в руках пользователя | ZIP / launcher / install/uninstall/rollback proof |
| I21 | MediaEngine FULL_VIDEO_CONVERT: непрерывный 1080p H.264, source FPS | ffprobe, frame continuity on source |
| I22 | Отдельные реальные media cases помимо 14926 и 14176 | 2+ blind clips, visual/manual acceptance |
| I23 | Публичный git чист от личных медиа, токенов и весов без лицензии | Code review + secret/media scan |

Каждая строка: NOT_STARTED / PARTIAL / PASS / FAIL / BLOCKED. PASS только при evidence path + SHA + environment + observed result; CI Windows != PC пользователя. Не вводить фиктивный зелёный DONE. Для первого честного релиза Auto Edit I01-I20 и I22-I23 обязательны; I21 отдельная принятая ранее feature, не блокирует minimal FolderToReel, но должна быть сохранена в roadmap. P12-P14 отдельно позднее.

Новый candidate проходит стандартные V52 257 acceptance регрессии при малейшей интеграции. Принятый stable не менять до manual promotion. Любой неполный release подписать RC / candidate, не FINAL.