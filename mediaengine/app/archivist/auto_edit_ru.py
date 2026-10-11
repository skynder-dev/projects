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
    "Skipped:": "Пропущено:", "Requested": "Запрошено", "got": "получилось",
    "there were not enough different moments in this footage for a longer reel.": "в этом материале не хватило разных моментов на более длинный ролик.",
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
