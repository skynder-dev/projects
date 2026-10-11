"""Russian interface for the Auto Edit pages (optional; English stays the default).

Only visible TEXT is translated - between tags and in placeholder / title attributes - never scripts, styles,
URLs or form values, so the pages work exactly the same in both languages. Longer phrases are replaced first.
"""
from __future__ import annotations

import re

PHRASES = {
    # navigation and frame
    "Home": "Главная", "Auto Edit": "Автомонтаж", "Media": "Медиа", "Devices": "Устройства", "Cloud": "Облако",
    "Activity": "Активность", "Settings": "Настройки", "Restart": "Перезапуск", "Quit": "Выход",
    "Working…": "Работаю…", "Open activity": "Активность",
    # home
    "Choose a folder of videos (or single videos), pick length, format and sound, and MediaEngine builds a reel from the best moments.":
        "Выбери папку с видео (или отдельные видео), длину, формат и звук — MediaEngine смонтирует ролик из лучших моментов.",
    "Your original files are only read, never changed.": "Оригиналы только читаются и никогда не меняются.",
    "New reel": "Новый ролик", "Choose folder…": "Выбрать папку…", "Choose videos…": "Выбрать видео…",
    "or paste a folder path, e.g. D:\\Videos\\Trip": "или вставь путь к папке, например D:\\Видео\\Поездка",
    "Continue": "Дальше", "My projects": "Мои проекты", "Show archived": "Показать архив", "Hide archived": "Скрыть архив",
    "Check this PC": "Проверка компьютера", "model, video tools and a 5-second test reel": "модель, видеоинструменты и тестовый ролик на 5 секунд",
    "No Auto Edit projects yet. Choose a folder with your videos to make the first one.":
        "Проектов пока нет. Выбери папку с видео, чтобы сделать первый ролик.",
    "AI model (FAST_LOCAL) not found.": "ИИ-модель (FAST_LOCAL) не найдена.",
    "Choose model folder…": "Выбрать папку с моделью…",
    "chosen video(s)": "выбранных видео", "video file(s) in folder": "видео в папке", "revision(s)": "версий",
    "Not exported yet": "Ещё не экспортирован", "Last export:": "Последний экспорт:",
    "Source videos are not available (drive disconnected?)": "Исходные видео недоступны (диск отключён?)",
    "Review": "Смотреть", "Open": "Открыть", "Export": "Экспорт", "Open video": "Открыть видео",
    "Show in folder": "Показать в папке", "Archive": "В архив", "Unarchive": "Из архива", "Copy path": "Копировать путь",
    "Copied": "Скопировано",
    # setup
    "Auto Edit · new reel": "Автомонтаж · новый ролик", "usable video(s)": "пригодных видео", "total": "всего",
    "skipped": "пропущено", "Show files": "Показать файлы", "File": "Файл", "Size": "Размер", "Length": "Длина",
    "Frame": "Кадр", "Format": "Формат", "Sound": "Звук", "recommended": "рекомендуется", "Create reel": "Создать ролик",
    "AI model not available.": "ИИ-модель недоступна.", "Build with Technical only": "Собрать без ИИ (только техника)",
    "Social HD (vertical 1080×1920)": "Social HD (вертикально 1080×1920)", "Vertical (540×960)": "Вертикально (540×960)",
    "Horizontal (960×540)": "Горизонтально (960×540)", "Social HD": "Social HD", "Vertical": "Вертикально",
    "Horizontal": "Горизонтально", "Auto (keep source sound, mute if it jumps)": "Авто (звук исходника, без звука если скачет)",
    "Source sound": "Звук исходника", "Mute": "Без звука", "Auto": "Авто", "Source": "Исходный",
    "a short reel is recommended": "лучше короткий ролик", "of usable video": "пригодного видео",
    # progress
    "Waiting": "В очереди", "Starting": "Запуск", "Checking files": "Проверка файлов", "Finding moments": "Поиск моментов",
    "Choosing moments": "Выбор моментов", "Checking clip edges": "Проверка краёв клипов", "Rendering segments": "Рендер кусков",
    "Joining and verifying": "Склейка и проверка", "Ready": "Готово", "Failed": "Ошибка", "Cancelled": "Отменено",
    "Cancel": "Отменить", "Retry": "Повторить", "Build failed": "Сборка не удалась", "Build cancelled": "Сборка отменена",
    "Build without AI (Technical only)": "Собрать без ИИ (только техника)",
    # project / review
    "All projects": "Все проекты", "Rename": "Переименовать", "Done": "Готово", "Your reel is saved": "Ролик сохранён",
    "checked against the accepted version (SHA-256)": "проверен по принятой версии (SHA-256)",
    "Moments in this reel": "Моменты в ролике", "Play in reel": "Показать в ролике", "View in source": "Открыть в исходнике",
    "from": "с", "to": "по", "replace with": "заменить на", "— keep —": "— оставить —", "remove": "убрать",
    "add a moment": "добавить момент", "Move up": "Выше", "Move down": "Ниже",
    "Times are in the source file. Every change makes a new version; this one stays as it is.":
        "Время — в исходном файле. Каждая правка создаёт новую версию, эта остаётся как есть.",
    "Apply my edits": "Применить правки",
    "Let MediaEngine choose again without removed moments": "Пусть MediaEngine выберет заново без убранных моментов",
    "Accept this version": "Принять эту версию", "Accepted": "Принята", "Revert": "Вернуть прежнюю",
    "Export MP4": "Экспорт MP4", "Export to another folder…": "Экспорт в другую папку…", "Saves to": "Сохраняет в",
    "Exported": "Экспортировано", "Compare blind with": "Сравнить вслепую с", "Compare": "Сравнить",
    "Make a variant": "Сделать вариант", "Make variant": "Сделать вариант", "Build reel": "Собрать ролик", "Build": "Собрать",
    "The current revision stays as it is. It keeps its removed moments and your edits; changing only format or sound reuses the analysis.":
        "Текущая версия не меняется. Убранные моменты и правки сохраняются; смена только формата или звука использует готовый анализ.",
    "Revisions": "Версии", "accepted": "принята", "viewing": "открыта", "edited by you": "твои правки", "excluded": "убрано",
    "Revision": "Версия", "sound": "звук", "Technical only (no AI)": "Только техника (без ИИ)", "AI moments (FAST_LOCAL)": "ИИ-моменты (FAST_LOCAL)",
    "Auto → original sound": "Авто → звук исходника",
    "Auto → muted (some moments have no sound; choose Source to keep the sound)":
        "Авто → без звука (в части моментов нет звука; выбери «Исходный», чтобы оставить звук)",
    "Auto → muted (no useful sound found)": "Авто → без звука (полезного звука нет)",
    "overlapping moment(s) of the same video were left out so nothing repeats":
        "пересекающихся моментов одного видео убрано, чтобы ничего не повторялось",
    "for this length the best": "для такой длины сравнивались лучшие", "moments were compared": "моментов",
    "HDR video could not be converted on this PC: colours may look grey": "HDR-видео не удалось перевести на этом компьютере: цвета могут быть серыми",
    "lower quality (analysis preview) used for:": "пониженное качество (копия для анализа) использовано для:",
    "- the original could not be re-cut": "— оригинал не удалось обработать",
    "HDR video converted to normal colours:": "HDR-видео переведено в обычные цвета:",
    "camcorder video de-interlaced:": "видео с камеры (чересстрочное) преобразовано в обычное:",
    "wide picture stored in narrow pixels shown in its real shape:": "широкая картинка из «узких» пикселей показана в правильных пропорциях:",
    "Not enough free space on the data drive:": "Мало места на диске с данными:", "GB.": "ГБ.",
    "A reel needs at least 1 GB to work in. Free some space (for example 'Free cache' on old projects) and try again.":
        "Для монтажа нужен хотя бы 1 ГБ. Освободи место (например, «Очистить кэш» в старых проектах) и попробуй снова.",
    "This folder has more than 64 videos. Use 'Choose videos…' to pick up to 64 of them, or choose a folder with fewer videos.":
        "В папке больше 64 видео. Нажми «Выбрать видео…» и выбери до 64 из них, или возьми папку, где видео меньше.",
    "Choose at most 64 videos for one reel.": "Для одного ролика можно выбрать не больше 64 видео.",
    "Other MediaEngine versions on this PC": "Другие версии MediaEngine на этом компьютере",
    "This one:": "Эта:",
    "Older versions are kept so you can go back to one; remove the ones you no longer need (projects and exports stay).":
        "Старые версии остаются, чтобы можно было вернуться; удали ненужные (проекты и ролики не пострадают).",
    "Remove this version? Your projects and exports are not affected.": "Удалить эту версию? Проекты и ролики не пострадают.",
    "Remove": "Удалить", "Removed": "Удалено", "· built": "· собрана",
    "That is not another MediaEngine version next to this one.": "Это не другая версия MediaEngine рядом с этой.",
    "Some files of that version are in use. Close anything opened from that folder and try again.":
        "Часть файлов этой версии занята. Закрой всё, что открыто из той папки, и попробуй снова.",
    "This folder has no supported video files": "В папке нет видео поддерживаемых форматов",
    "Not a supported video file:": "Неподдерживаемый файл:",
    "No videos directly in this folder.": "В самой папке видео нет.", "video(s)": "видео",
    "These folders inside it have videos — open one (or use Choose videos… to pick from several):":
        "Видео есть во вложенных папках — открой одну (или нажми «Выбрать видео…», чтобы взять из нескольких):",
    "Skipped:": "Пропущено:", "Requested": "Запрошено", "got": "получилось",
    "there were not enough different moments in this footage for a longer reel.": "в этом материале не хватило разных моментов на более длинный ролик.",
    "You found them about the same: A =": "Для тебя они примерно одинаковы: A =", "You preferred A =": "Ты выбрал A =",
    "You preferred B =": "Ты выбрал B =", "over B =": "вместо B =", "over A =": "вместо A =", "· automatic)": "· автоматически)",
    "· edited by you)": "· с твоими правками)", "Blind comparison": "Слепое сравнение", "Note:": "Заметка:",
    "Project not found": "Проект не найден", "Comparison not found": "Сравнение не найдено",
    " s · ": " с · ", " s ·": " с ·", "· Vertical ": "· Вертикально ", "· Landscape ": "· Горизонтально ",
    "Vertical ·": "Вертикально ·", "Landscape ·": "Горизонтально ·", "· Horizontal ": "· Горизонтально ", "Horizontal ·": "Горизонтально ·",
    "First time on this PC?": "Первый раз на этом компьютере?",
    "Check this PC first: it shows whether the AI model and video tools are found and builds a 5-second test reel (about a minute; your videos are not used).":
        "Сначала проверь компьютер: видно, найдены ли ИИ-модель и видеоинструменты, и собирается тестовый ролик на 5 секунд (около минуты; твои видео не используются).",
    # skip reasons (inside "Skipped: name (reason)") and why a build stopped
    "marked Private in the library": "отмечено как Private в библиотеке", "no usable moments found": "не найдено пригодных моментов",
    "almost no movement (still image)": "почти нет движения (застывшая картинка)", "too short to analyse": "слишком короткое для анализа",
    "analysis took too long": "анализ шёл слишком долго", "could not be analysed": "не удалось проанализировать",
    "damaged or not a video": "повреждено или не видео", "duplicate of ": "дубль файла ", "(too short)": "(слишком короткое)", "(no video)": "(нет видео)",
    "The AI model files are missing or not the exact pinned version.": "Файлов ИИ-модели нет или это не та самая проверенная версия.",
    "No supported video files in the folder.": "В папке нет видео поддерживаемых форматов.",
    "The folder has more than 64 videos.": "В папке больше 64 видео.", "Analysis of the footage failed.": "Анализ видео не удался.",
    "A chosen moment no longer exists (the source files changed or the cache was freed). Use 'Let MediaEngine choose again' or make a new reel.":
        "Выбранного момента больше нет (исходники изменились или кэш очищен). Нажми «Пусть MediaEngine выберет заново» или сделай новый ролик.",
    "None of the videos could be analysed (too short, still images or damaged).": "Ни одно видео не удалось проанализировать (слишком короткие, застывшие или повреждённые).",
    "All moments were removed. Remove fewer moments or let MediaEngine choose again.": "Убраны все моменты. Убери меньше или пусть MediaEngine выберет заново.",
    "This format is not available.": "Этот формат недоступен.",
    "Two chosen videos have the same file name. Rename one of them.": "У двух выбранных видео одинаковые имена. Переименуй одно из них.",
    "A rendered piece could not be read back. Try again; if it repeats, free the cache.": "Собранный кусок не читается. Попробуй ещё раз; если повторится — очисти кэш.",
    "The source file of a trimmed moment is not available.": "Исходный файл обрезанного момента недоступен.",
    "A trimmed moment is shorter than 0.5 s.": "Обрезанный момент короче 0,5 с.",
    "None of the videos in the folder can be used (damaged, duplicate or marked Private).": "Ни одно видео из папки нельзя использовать (повреждено, дубль или Private).",
    "The source folder is not available.": "Папка с исходниками недоступна.",
    "Not enough different moments for this length. Try a shorter length.": "Для такой длины не хватает разных моментов. Выбери длину покороче.",
    "No usable moments were found. Try a shorter length or other footage.": "Пригодных моментов не найдено. Выбери длину покороче или другие видео.",
    "Test reel built": "Тестовый ролик собран", "Test reel failed": "Тестовый ролик не собрался",
    "with the AI model (FAST_LOCAL)": "с ИИ-моделью (FAST_LOCAL)", "The AI mode works on this PC.": "ИИ-режим на этом компьютере работает.",
    # why an action was refused (error pages)
    "A single moment can be at most 60 s": "Один момент — не длиннее 60 с", "A trimmed moment must be at least 0.5 s long": "Обрезанный момент — не короче 0,5 с",
    "Accepted revision changed on disk; export refused": "Принятая версия изменилась на диске; экспорт отменён",
    "At most 30 moments in one reel": "В одном ролике — не больше 30 моментов",
    "Choose a different folder: the source folder of this reel would then contain the reel itself":
        "Выбери другую папку: иначе ролик окажется в папке с его же исходниками",
    "Choose a folder outside Private / Rejected for exports": "Для экспорта выбери папку вне Private / Rejected",
    "Choose two different versions": "Выбери две разные версии", "Choose two versions of this project": "Выбери две версии этого проекта",
    "Export folder not found:": "Папка для экспорта не найдена:", "File not found:": "Файл не найден:",
    "Length must be a number of seconds": "Длина — число секунд", "Length must be one of": "Длина должна быть одной из:",
    "No exact FAST_LOCAL model found there": "Там нет точной модели FAST_LOCAL",
    "Not a time:": "Это не время:", "(use seconds like 12.5 or minutes like 1:05)": "(пиши секунды, например 12.5, или минуты, например 1:05)",
    "Revision file changed on disk; it cannot be accepted": "Файл версии изменился на диске; принять её нельзя",
    "Revision not found in this project": "В этом проекте нет такой версии",
    "The AI model (FAST_LOCAL) is not available on this computer. Choose 'Technical only' explicitly or install the model.":
        "ИИ-модели (FAST_LOCAL) на этом компьютере нет. Выбери «Только техника» явно или установи модель.",
    "The same moment is used twice": "Один и тот же момент использован дважды",
    "The source videos are not available (disconnected drive?)": "Исходные видео недоступны (диск отключён?)",
    "This comparison was already decided": "Это сравнение уже завершено", "Times must be zero or more seconds": "Время — ноль или больше секунд",
    "Title is empty": "Название пустое", "Unknown choice": "Неизвестный выбор", "Unknown format": "Неизвестный формат",
    "Unknown selection mode": "Неизвестный режим отбора", "Unknown sound option": "Неизвестный вариант звука",
    "Two chosen files have the same name (": "У двух выбранных файлов одинаковое имя (", "). Rename one of them, or choose a folder.": "). Переименуй один или выбери папку.",
    "Blind comparisons": "Слепые сравнения", "preferred over": "лучше, чем", "about the same": "примерно одинаково",
    "Space used: versions": "Занято: версии", "analysis cache": "кэш анализа", "Free cache": "Очистить кэш",
    "(can be freed; the next build then analyses the videos again)": "(можно очистить; следующая сборка заново проанализирует видео)",
    # blind comparison
    "Auto Edit · blind comparison": "Автомонтаж · слепое сравнение", "A is better": "A лучше", "B is better": "B лучше",
    "About the same": "Примерно одинаково", "Result": "Результат", "Back to the project": "Назад к проекту",
    "Watch both. Which one would you rather publish? Versions and settings are hidden until you decide.":
        "Посмотри оба. Какой бы ты опубликовал? Версии и настройки скрыты, пока ты не решишь.",
    "Why? (optional, e.g. better start, fewer shaky shots)": "Почему? (необязательно, например «лучше начало, меньше тряски»)",
    # check page
    "What MediaEngine needs, and a 5-second test reel made from generated clips (your videos are not used).":
        "Что нужно MediaEngine, и тестовый ролик на 5 секунд из сгенерированных клипов (твои видео не используются).",
    "Build a test reel": "Собрать тестовый ролик", "Build a test reel with the AI model": "Собрать тестовый ролик с ИИ-моделью",
    "Program folder": "Папка программы", "Data folder (projects, exports)": "Папка данных (проекты, экспорт)",
    "Free space on the data drive": "Свободно на диске данных", "Engine libraries load (numpy, OpenCV, ONNX Runtime)": "Библиотеки движка загружаются (numpy, OpenCV, ONNX Runtime)",
    "HDR phone video conversion (zscale)": "Перевод HDR-видео с телефона (zscale)", "Processor": "Процессор", "Windows long paths": "Длинные пути Windows",
    "Back": "Назад", "Could not continue": "Не получилось продолжить",
    # mixed lines and labels
    "Social HD · vertical 1080×1920": "Social HD · вертикально 1080×1920", "Vertical 540×960": "Вертикально 540×960",
    "Horizontal 960×540": "Горизонтально 960×540", " · recommended": " · рекомендуется", ", total ": ", всего ",
    "Only ": "Всего ", "Without it MediaEngine can only use the ": "Без неё MediaEngine умеет только режим ",
    " selection (sharpness, motion, exposure); it does not understand what happens in the video.":
        " (резкость, движение, свет); что происходит в кадре, он не понимает.",
    "Without it reels use the clearly labelled ": "Без неё ролики собираются в явно отмеченном режиме ",
    " selection. If you have the model (for example in an existing Archivist install), choose its folder: the exact files are verified and copied here.":
        ". Если модель есть (например, в рабочем Archivist), выбери её папку: файлы проверяются по хешам и копируются сюда.",
    "· source ": "· исходник ", "Revision R": "Версия R", "Horizontal ·": "Горизонтально ·", "Vertical ·": "Вертикально ·",
    " excluded": " убрано", "· sound auto": "· звук авто", "· sound mute": "· без звука", "· sound source": "· звук исходника",
    "· sound Авто": "· звук Авто", "· sound Auto": "· звук Авто", "· sound Mute": "· без звука", "· sound Source": "· звук исходника",
    "Waiting:": "В очереди:", " elapsed": " прошло", "Technical only": "Только техника",
    "READY": "ГОТОВ", "REVIEW": "ПРОСМОТР", "DRAFT": "ЧЕРНОВИК", "PROCESSING": "СБОРКА", "ATTENTION": "ВНИМАНИЕ",
    "Test reel built": "Тестовый ролик собран", "with the AI model (FAST_LOCAL)": "с ИИ-моделью (FAST_LOCAL)",
    "reel from two generated clips · stages:": "ролик из двух сгенерированных клипов · этапы:", "Test reel failed after": "Тестовый ролик не собрался за",
    "The source videos are not available (drive disconnected?). Revisions and exports are kept; new builds are possible when they are back.":
        "Исходные видео недоступны (диск отключён?). Версии и экспорт сохранены; новые сборки — когда видео вернутся.",
    "The disk is full. Free some space (for example 'Free cache' on old projects) and press Retry.":
        "Диск заполнен. Освободи место (например, «Очистить кэш» в старых проектах) и нажми «Повторить».",
    "Windows refused access to a file (another program may be using it). Close it and press Retry.":
        "Windows не дал доступ к файлу (его может держать другая программа). Закрой её и нажми «Повторить».",
    "The PC ran out of memory. Close other programs or choose fewer / shorter videos, then Retry.":
        "Не хватило памяти. Закрой другие программы или возьми меньше / короче видео и нажми «Повторить».",
    "Interrupted: the app was closed. Press Retry - finished analysis is reused.":
        "Прервано: программа была закрыта. Нажми «Повторить» — готовый анализ используется снова.",
    "Русский": "Русский", "English": "English",
    "available": "есть", "missing - HDR video will look grey": "нет — HDR-видео будет серым",
    "not found - only 'Technical only' reels": "не найдена — только режим «Только техника»",
    "files changed or incomplete - not used": "файлы изменены или неполные — не используется",
    "logical cores": "логических ядер", "on": "включены",
    "off (handled: long-named videos are analysed under short names)": "выключены (учтено: видео с длинными именами анализируются под короткими)",
    "Without the AI model, tick 'Build with Technical only' to continue.": "Без ИИ-модели поставь галочку «Собрать без ИИ (только техника)».",
    "Wait until the current build has finished": "Дождись окончания текущей сборки",
    "Folder not found": "Папка не найдена", "No video files chosen": "Видео не выбраны",
    "Private and Rejected media cannot be used in a reel": "Видео из Private и Rejected нельзя использовать в ролике",
    "Accept a revision before exporting": "Сначала прими версию (Accept), потом экспорт",
    "This page can only be opened from MediaEngine itself.": "Эту страницу можно открыть только из самого MediaEngine.",
}

import html as _html
# the pages escape quotes (' -> &#x27;): look for both spellings
for _en, _ru in list(PHRASES.items()):
    _esc = _html.escape(_en, quote=True)
    if _esc != _en:
        PHRASES[_esc] = _html.escape(_ru, quote=True)

_WORD_LIKE = re.compile(r"^[A-Za-z]+$")
# plain single words ("Export", "Home") only when they are the whole text of an element - so a project title,
# file name or path that merely contains such a word is never changed; longer phrases anywhere in the text
_EXACT = {en: ru for en, ru in PHRASES.items() if _WORD_LIKE.match(en)}
_ORDERED = sorted(((en, ru) for en, ru in PHRASES.items() if not _WORD_LIKE.match(en)), key=lambda kv: -len(kv[0]))
_SPLIT = re.compile(r"(<script\b.*?</script>|<style\b.*?</style>|<[^>]+>)", re.S | re.I)
_ATTR = re.compile(r"""(\b(?:placeholder|title)=)(['"])(.*?)\2""", re.S)
_PROTECT = re.compile(r"""<(\w+)\b[^>]*(?:translate=['"]no['"]|class=['"][^'"]*\bae-path\b[^'"]*['"])[^>]*>.*?</\1>""", re.S)


def _translate_text(t: str) -> str:
    core = t.strip()
    if not core:
        return t
    if core in _EXACT:
        return t.replace(core, _EXACT[core])
    for en, ru in _ORDERED:
        if en in t:
            t = t.replace(en, ru)
    return t


# messages written by the page scripts (only these exact quoted strings are replaced inside <script>)
JS_PHRASES = {
    "' elapsed'": "' прошло'", "' · about '": "' · примерно '", "' min left'": "' мин осталось'",
    "' · less than a minute left'": "' · меньше минуты осталось'",
    "'A Windows folder window is open — it may be behind this window.'": "'Открыто окно выбора папки Windows — оно может быть за этим окном.'",
    "'A Windows window is open — it may be behind this window. Ctrl+click to choose several videos.'":
        "'Открыто окно Windows — оно может быть за этим окном. Ctrl+щелчок — выбрать несколько видео.'",
    "'Checking the videos… (a few seconds per video)'": "'Проверяю видео… (несколько секунд на каждое)'",
    "'Checking the videos…'": "'Проверяю видео…'", "'Building the test reel… (up to a few minutes)'": "'Собираю тестовый ролик… (до нескольких минут)'",
    "'Choose the folder that contains FAST_LOCAL…'": "'Выбери папку, в которой лежит FAST_LOCAL…'",
    "'Model installed.'": "'Модель установлена.'", "'Not installed'": "'Не установлена'",
    "'Copied'": "'Скопировано'", "'Copy this path:'": "'Скопируй путь:'", "'Folder window failed: '": "'Окно выбора папки не открылось: '",
    "'No folder chosen.'": "'Папка не выбрана.'", "'No videos chosen.'": "'Видео не выбраны.'", "'Window failed: '": "'Окно не открылось: '",
    "' of '": "' из '",
}


def _translate_script(block: str) -> str:
    for en, ru in JS_PHRASES.items():
        block = block.replace(en, ru)
    return block


def translate_html(html: str) -> str:
    kept = []

    def hold(m):
        kept.append(m.group(0))
        return f"\x00{len(kept) - 1}\x00"
    html = _PROTECT.sub(hold, html)      # paths and user content (translate='no') stay exactly as they are
    out = []
    for part in _SPLIT.split(html):
        if not part:
            continue
        if part.startswith("<"):
            low = part[:8].lower()
            if low.startswith("<script"):
                out.append(_translate_script(part))
            elif low.startswith("<style"):
                out.append(part)
            else:
                out.append(_ATTR.sub(lambda m: m.group(1) + m.group(2) + _translate_text(m.group(3)) + m.group(2), part))
        else:
            out.append(_translate_text(part))
    html = "".join(out)
    return re.sub("\x00(\\d+)\x00", lambda m: kept[int(m.group(1))], html)
