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
    "only in the cloud (OneDrive), not on this PC: choose 'Always keep on this device' first":
        "только в облаке OneDrive, на компьютере его нет: сначала выбери «Всегда сохранять на этом устройстве»",
    "only in the cloud (OneDrive), not on this PC: choose &#x27;Always keep on this device&#x27; first":
        "только в облаке OneDrive, на компьютере его нет: сначала выбери «Всегда сохранять на этом устройстве»",
    "These videos are only in OneDrive, not on this PC. In Explorer right-click the folder → 'Always keep on this device', wait until the download is done, then choose it again.":
        "Эти видео лежат только в OneDrive, на компьютере их нет. В Проводнике щёлкни папку правой кнопкой → «Всегда сохранять на этом устройстве», дождись загрузки и выбери папку снова.",
    "skipped": "пропущено", "skipped: ": "пропущено: ", "usable": "годится",
    "very short — may be skipped": "очень короткое — может быть пропущено",
    "Preparing a recording without a length: ": "Подготовка записи без длины: ",
    # AI+ (optional stronger model)
    "AI — as before (fast)": "ИИ — как раньше (быстро)",
    "AI+ — stronger model, first analysis slower": "ИИ+ — модель сильнее, первый анализ дольше",
    "How moments are chosen": "Как выбирать моменты",
    "AI+ (a stronger model, PE-Core L/14) can be added once on ": "ИИ+ (модель сильнее, PE-Core L/14) можно один раз добавить на странице ",
    " (about 650 MB, free).": " (около 650 МБ, бесплатно).", "Stop": "Остановить",
    "AI+ moments (PE-Core L/14)": "ИИ+-моменты (PE-Core L/14)",
    "AI+ model is installed": "Модель ИИ+ установлена",
    "PE-Core L/14 (Meta, Apache-2.0), every file is checked. Choose AI+ when you make a reel or a variant, and compare it with AI using Compare blind.":
        "PE-Core L/14 (Meta, Apache-2.0), каждый файл проверен. Выбирай ИИ+ при создании ролика или варианта и сравнивай с ИИ кнопкой «Сравнить вслепую».",
    "AI+ — a stronger model (optional)": "ИИ+ — модель сильнее (по желанию)",
    "PE-Core L/14 (Meta, Apache-2.0) understands people, what they do and the things around them much better than the built-in AI model (tested on public photos: it finds the right photo for a description in 86 of 100 cases, the built-in model in 60); for plain landscapes the difference is small. It works on this PC without internet; the first analysis of new videos is slower (about 1–2 s per checked frame). ":
        "PE-Core L/14 (Meta, Apache-2.0) намного лучше встроенной модели понимает людей, что они делают и что вокруг них (проверено на открытых фото: правильное фото по описанию находит в 86 случаях из 100, встроенная модель — в 60); на простых пейзажах разница небольшая. Работает на этом компьютере без интернета; первый анализ новых видео дольше (примерно 1–2 с на каждый проверяемый кадр). ",
    "Download once: ": "Скачать один раз: ", ", from huggingface.co (free); every file is checked.": ", с huggingface.co (бесплатно); каждый файл проверяется.",
    "Download AI+ model": "Скачать модель ИИ+", "Continue the download": "Продолжить скачивание", "Copy from a folder…": "Скопировать из папки…",
    "Build a test reel with AI+": "Собрать тестовый ролик с ИИ+",
    "with the AI+ model (PE-Core L/14)": "с моделью ИИ+ (PE-Core L/14)", "The AI+ mode works on this PC.": "Режим ИИ+ работает на этом компьютере.",
    "AI+ model (PE-Core L/14, optional)": "Модель ИИ+ (PE-Core L/14, по желанию)",
    "not downloaded yet (optional) - see AI+ below": "ещё не скачана (по желанию) — см. ИИ+ ниже",
    "The AI+ model is not on this computer yet. Download it once on 'Check this PC' or choose another mode.":
        "Модели ИИ+ на этом компьютере пока нет. Скачай её один раз на странице «Проверка компьютера» или выбери другой режим.",
    "The AI+ model files are missing or changed. Download the AI+ model again on 'Check this PC'.":
        "Файлов модели ИИ+ нет или они изменены. Скачай модель ИИ+ заново на странице «Проверка компьютера».",
    "Download cancelled.": "Скачивание остановлено.",
    "No exact AI+ model there (vision_model_int8.onnx, text_model_int8.onnx, vocab.json, merges.txt).":
        "Там нет точной модели ИИ+ (vision_model_int8.onnx, text_model_int8.onnx, vocab.json, merges.txt).",
    "Only from MediaEngine itself.": "Только из самой программы MediaEngine.",
    "loading the AI+ model": "загрузка модели ИИ+",
    "The AI+ model is being downloaded": "Сейчас скачивается модель ИИ+",
    "The Library search by theme is being prepared": "Сейчас готовится поиск по темам в библиотеке",
    "The AI+ model is being downloaded right now. Wait until it is finished or stop it first.":
        "Модель ИИ+ сейчас скачивается. Дождись конца или сначала останови скачивание.",
    "The AI+ model could not be started (not enough memory?). Close other programs and press Retry, or use AI.":
        "Модель ИИ+ не запустилась (не хватает памяти?). Закрой другие программы и нажми «Повторить» или используй ИИ.",
    "Technical only (sharpness, motion, exposure)": "Только техника (резкость, движение, яркость)",
    "Theme (AI+)": "Тема (ИИ+)", "No theme — the best moments": "Без темы — лучшие моменты",
    "With a theme, AI+ looks through all the videos for moments that match it (for example only the sea).":
        "С темой ИИ+ ищет во всех видео подходящие моменты (например, только море).",
    "Sea and beach": "Море и пляж", "Mountains": "Горы", "Children": "Дети", "Family and friends": "Семья и друзья",
    "Celebration": "Праздник", "Animals": "Животные", "Sunset": "Закат", "Nature": "Природа", "Winter and snow": "Зима и снег",
    "City": "Город", "Food": "Еда", "Sport": "Спорт", "Road trip": "Дорога и поездки", "theme": "тема",
    "Music and title": "Музыка и надпись", "(optional)": "(по желанию)", "Title at the start": "Надпись в начале",
    "For example: Summer at the sea": "Например: Лето у моря", "Second line": "Вторая строка",
    "For example: July 2026": "Например: июль 2026", "Insert the date": "Вставить дату",
    "Music (your own audio file: mp3, m4a, wav, flac, ogg)": "Музыка (твой аудиофайл: mp3, m4a, wav, flac, ogg)",
    "Choose music…": "Выбрать музыку…", "No music": "Без музыки",
    "Music and the videos' sound (quieter)": "Музыка и звук видео (тише)", "Only music": "Только музыка",
    "The title is shown for the first 3 seconds. The music starts softly and fades out at the end; a short song is repeated. "
    "Changing music or title later makes a new version quickly, without a new analysis.":
        "Надпись видна первые 3 секунды. Музыка начинается плавно и затихает в конце; короткая песня повторяется. "
        "Если потом поменять музыку или надпись, новая версия соберётся быстро, без нового анализа.",
    "No music chosen. You can also paste the path.": "Музыка не выбрана. Можно вставить путь к файлу.",
    "the title could not be drawn: no suitable font on this PC": "надпись не нарисована: на этом компьютере нет подходящего шрифта",
    "title: ": "надпись: ", "music: ": "музыка: ", " (only music)": " (только музыка)", " (with the videos' sound)": " (со звуком видео)",
    "A title can be at most 80 characters long": "Надпись — не длиннее 80 знаков",
    "Music file not found:": "Файл музыки не найден:", "Not a music file:": "Это не музыкальный файл:",
    "The music file is not there any more. Choose it again or make the version without music.":
        "Файла музыки больше нет на месте. Выбери его снова или собери версию без музыки.",
    "The chosen music is not an audio file (mp3, m4a, wav, flac, ogg...).": "Выбранная музыка — не аудиофайл (mp3, m4a, wav, flac, ogg…).",
    "The chosen music file has no sound that can be read. Choose another file.": "В выбранном файле музыки нет звука, который можно прочитать. Выбери другой файл.",
    "few moments match the theme, so the reel also uses other good moments": "мало моментов на эту тему, поэтому в ролике есть и другие хорошие моменты",
    "moments that match the theme: ": "моментов на эту тему: ",
    "length was not written in the file (browser or screen recording) — a fixed copy is used, the original is not changed":
        "длина не записана в файле (запись из браузера или с экрана) — используется исправленная копия, оригинал не меняется", "Show files": "Показать файлы", "File": "Файл", "Size": "Размер", "Length": "Длина",
    "Frame": "Кадр", "Format": "Формат", "Sound": "Звук", "recommended": "рекомендуется", "Create reel": "Создать ролик",
    "AI model not available.": "ИИ-модель недоступна.", "Build with Technical only": "Собрать без ИИ (только техника)",
    "Build without AI (Technical only: sharpness, motion, exposure)":
        "Собрать без ИИ (только техника: резкость, движение, свет)",
    "Social HD (vertical 1080×1920)": "Social HD (вертикально 1080×1920)", "Vertical (540×960)": "Вертикально (540×960)",
    "Horizontal (960×540)": "Горизонтально (960×540)", "Social HD": "Social HD", "Vertical": "Вертикально",
    "Horizontal": "Горизонтально", "Auto (keep source sound, mute if it jumps)": "Авто (звук исходника; без звука, если он есть не везде)",
    "Source sound": "Звук исходника", "Mute": "Без звука", "Auto": "Авто", "Source": "Исходный",
    "a short reel is recommended": "лучше короткий ролик", "of usable video": "пригодного видео",
    "A lot of video. The first build analyses all of it once and can take a long time; later builds and variants reuse that analysis. The PC does not go to sleep while MediaEngine works, and you can keep using it.":
        "Много видео. Первая сборка один раз анализирует всё и может идти долго; следующие сборки и варианты используют готовый анализ. Пока MediaEngine работает, компьютер не уснёт, и им можно пользоваться.",
    # progress
    "Waiting": "В очереди", "Starting": "Запуск", "Checking files": "Проверка файлов", "Finding moments": "Поиск моментов",
    "Choosing moments": "Выбор моментов", "Checking clip edges": "Проверка краёв клипов", "Rendering segments": "Нарезка кусков",
    "Joining and verifying": "Склейка и проверка", "Ready": "Готово", "Failed": "Ошибка", "Cancelled": "Отменено",
    # what the engine reports while it works (job message line)
    "building moment library": "собираю библиотеку моментов", "checking clip boundaries": "проверяю границы моментов",
    "joining segments and verifying": "склеиваю куски и проверяю", "choosing moments": "выбираю моменты",
    "analysing videos": "анализирую видео", "technical analysis": "технический анализ",
    "Cancel": "Отменить", "Retry": "Повторить", "Build failed": "Сборка не удалась", "Build cancelled": "Сборка отменена",
    "Build without AI (Technical only)": "Собрать без ИИ (только техника)",
    # project / review
    "All projects": "Все проекты", "Rename": "Переименовать", "Done": "Готово", "Your reel is saved": "Ролик сохранён",
    "checked against the accepted version (SHA-256)": "проверен: точно совпадает с принятой версией",
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
    # a folder with more videos than one reel takes: pick a day or tick videos
    "One reel can use up to 64 of them: pick a day, or tick the videos you want.":
        "В один ролик можно взять до 64: выбери день или отметь нужные видео.",
    "Only the videos directly in this folder are used. Folders inside it with videos: ":
        "Берутся только видео, лежащие прямо в этой папке. Вложенных папок с видео: ",
    "Exported reels": "Готовые ролики", "The folder for exported reels is not there yet.": "Папки с готовыми роликами ещё нет.",
    "You can close this window: the reel keeps building and the PC does not go to sleep. Open MediaEngine again to see it.":
        "Окно можно закрыть: ролик продолжит собираться, а компьютер не уснёт. Чтобы посмотреть, снова открой MediaEngine.",
    "The current revision stays as it is. Format and sound variants keep its removed moments and your edits and reuse the analysis; a new length chooses the moments again (removed ones stay out).":
        "Текущая версия не меняется. Варианты с другим форматом или звуком сохраняют убранные моменты и твои правки и используют готовый анализ; при другой длине моменты выбираются заново (убранные так и остаются убранными).",
    "This version already exists: R": "Такая версия уже есть: R",
    " (the same settings and moments). Change the length, format or sound, or tick “remove” on a moment.":
        " (те же настройки и моменты). Измени длину, формат или звук либо отметь «убрать» у момента.",
    "The reel is shorter than ": "Ролик короче ",
    " s because you removed or trimmed moments. Add a moment below or let MediaEngine choose again.":
        " с, потому что ты убрал или обрезал моменты. Добавь момент ниже или нажми «Пусть MediaEngine выберет заново».",
    " · from ": " · из папки ",
    "your trim": "твоя обрезка", "edge trimmed": "край подрезан",
    "That is a file, not a folder. Paste the path of a folder, or press Choose videos….":
        "Это файл, а не папка. Вставь путь к папке или нажми «Выбрать видео…».",
    " s (requested ": " с (выбрано ", " s) · ": " с) · ", "Undo accept": "Отменить принятие",
    "These folders inside it have videos — open one (or use Choose videos… on the Auto Edit page to pick from several):":
        "Видео есть во вложенных папках — открой одну (или нажми «Выбрать видео…» на странице автомонтажа, чтобы взять из нескольких):",
    "Accept R": "Принять R",
    "Other days of this folder": "Другие дни этой папки", "Folder above": "Папка выше",
    "Go to Auto Edit": "Перейти к автомонтажу", "The test reel is not there (build it on Check this PC).":
        "Тестового ролика нет (собери его в «Проверке компьютера»).",
    "too short (under 2.5 s)": "слишком короткое (меньше 2,5 с)", "no video stream": "нет видеодорожки",
    "cannot be read (locked or no access)": "не читается (занято другой программой или нет доступа)",
    "No readable videos among the chosen files.": "Среди выбранных файлов нет читаемых видео.",
    "No readable videos in this folder.": "В этой папке нет читаемых видео.",
    "All these videos are shorter than 2.5 seconds - too short to find moments in.":
        "Все эти видео короче 2,5 секунды — в них не из чего выбрать моменты.",
    "A new version with your edits.": "Новая версия с твоими правками.",
    "A new version is being built from your choice. Editing is possible again when it is ready.":
        "Собирается новая версия по твоему выбору. Править можно будет, когда она будет готова.",
    "By day": "По дням", "Use this day": "Взять этот день", "more than 64 — tick them below": "больше 64 — отметь ниже",
    "The day is taken from the file name (e.g. VID_20260714_…), otherwise from the file's date.":
        "День берётся из имени файла (например, VID_20260714_…), иначе — из даты файла.",
    "Tick videos": "Отметить видео", "Tick the newest 64": "Отметить 64 самых новых", "Untick all": "Снять все отметки",
    "Ticked: ": "Отмечено: ", "Use the ticked videos": "Взять отмеченные видео",
    "More than 64 ticked — untick some.": "Отмечено больше 64 — сними лишние.",
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
        "Сначала нажми «Проверка компьютера»: она покажет, найдены ли ИИ-модель и видеоинструменты, и соберёт тестовый ролик на 5 секунд (около минуты; твои видео не используются).",
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
    "HDR phone video conversion (zscale)": "Преобразование HDR-видео с телефона (zscale)", "Processor": "Процессор", "Windows long paths": "Длинные пути Windows",
    "Back": "Назад", "Could not continue": "Не получилось продолжить",
    # mixed lines and labels
    "Social HD · vertical 1080×1920": "Social HD · вертикально 1080×1920", "Vertical 540×960": "Вертикально 540×960",
    "Horizontal 960×540": "Горизонтально 960×540", " · recommended": " · рекомендуется", ", total ": ", всего ",
    "Only ": "Всего ", "Without it MediaEngine can only use the ": "Без неё MediaEngine умеет только режим ",
    " selection (sharpness, motion, exposure); it does not understand what happens in the video.":
        " (резкость, движение, свет); что происходит в кадре, он не понимает.",
    "Without it reels use the clearly labelled ": "Без неё ролики собираются в явно отмеченном режиме ",
    " selection. If you have the model (for example in an existing Archivist install), choose its folder: the exact files are verified and copied here.":
        ". Если модель есть (например, в установленном раньше Archivist, D:\\Archivist), выбери её папку: файлы проверяются на точное совпадение и копируются сюда.",
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
    "Network folders can only be opened from MediaEngine itself: paste the path on the Auto Edit page.":
        "Сетевые папки открываются только из самого MediaEngine: вставь путь на странице «Автомонтаж».",
    "No video of this theme is on this PC now.": "Сейчас на этом компьютере нет видео на эту тему.",
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
    "' · final encode and check of the whole reel, can take a few minutes'": "' · сборка и проверка всего ролика, может занять несколько минут'",
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
    "'write the time as seconds (12.5) or minutes (1:05)'": "'напиши время в секундах (12.5) или минутах (1:05)'",
    "'“to” must be at least 0.5 s after “from”'": "'«по» должно быть хотя бы на 0,5 с позже, чем «с»'",
    "'one moment can be at most 60 s long'": "'один момент — не длиннее 60 с'",
    "'Moment '": "'Момент '", "'Starting…'": "'Запуск…'", "'Installed.'": "'Установлено.'", "'Failed'": "'Не получилось'", "'the video is only '": "'видео длится всего '",
    "' s long - “to” cannot be later'": "' с — «по» не может быть позже'",
    "' · waiting until the reel is built'": "' · жду, пока соберётся ролик'",
    "'A Windows window is open — it may be behind this window.'": "'Открыто окно Windows — оно может быть за этим окном.'",
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
