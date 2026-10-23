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
    "not downloaded yet - see AI+ below": "ещё не скачана — см. ИИ+ ниже", "built in": "собран за", "Settings saved.": "Настройки сохранены.",
    "No videos found yet. Add a folder above (or connect a phone, a card or a USB drive).": "Видео пока не найдены. Добавь папку выше (или подключи телефон, карту памяти или USB-диск).",
    "The Library is empty. Add a folder on Import and choose its videos for the Library.": "Библиотека пуста. Добавь папку на странице «Импорт» и выбери её видео для Библиотеки.",
    "Wait until the current build has finished, then archive the project.": "Дождись окончания текущей сборки, потом отправь проект в архив.",
    "The AI+ model is not on this computer yet. Download it once on 'Check this PC' or choose another mode.":
        "Модели ИИ+ на этом компьютере пока нет. Скачай её один раз на странице «Проверка компьютера» или выбери другой режим.",
    "The AI+ model files are missing or changed. Download the AI+ model again on 'Check this PC'.":
        "Файлов модели ИИ+ нет или они изменены. Скачай модель ИИ+ заново на странице «Проверка компьютера».",
    "Download cancelled.": "Скачивание остановлено.",
    "No exact AI+ model there (vision_model_int8.onnx, text_model_int8.onnx, vocab.json, merges.txt).":
        "Там нет точной модели ИИ+ (vision_model_int8.onnx, text_model_int8.onnx, vocab.json, merges.txt).",
    "Only from MediaEngine itself.": "Только из самой программы MediaEngine.",
    "loading the AI+ model": "загрузка модели ИИ+", "finding the beat of the music": "ищу ритм музыки",
    "The AI+ model is being downloaded": "Сейчас скачивается модель ИИ+",
    "The Library search by theme is being prepared": "Сейчас готовится поиск по темам в библиотеке",
    "AI+ is being prepared for the Library (it continues next time)": "Идёт подготовка ИИ+ для Библиотеки (в следующий раз продолжится с того же места)",
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
    "City": "Город", "Food": "Еда", "Sport": "Спорт", "Road trip": "Дорога и поездки", "Aerial view (drone)": "Вид сверху (дрон)", "theme": "тема",
    "Music and title": "Музыка и надпись", "(optional)": "(по желанию)", "Title at the start": "Надпись в начале",
    "For example: Summer at the sea": "Например: Лето у моря", "Second line": "Вторая строка",
    "For example: July 2026": "Например: июль 2026", "Insert the date": "Вставить дату",
    "Music (your own audio file: mp3, m4a, wav, flac, ogg)": "Музыка (твой аудиофайл: mp3, m4a, wav, flac, ogg)",
    "Choose music…": "Выбрать музыку…", "No music": "Без музыки",
    "Music and the videos' sound (quieter)": "Музыка и звук видео (тише)", "Only music": "Только музыка",
    "Cuts on the beat of the music": "Склейки в такт музыке", "(when the music has a clear beat)": "(если у музыки есть чёткий ритм)",
    "the music has no clear beat, so the cuts were left where they were": "у музыки нет чёткого ритма, поэтому склейки остались на своих местах",
    "cuts on the beat of the music: ": "склейки в такт музыке: ", "beats per minute": "ударов в минуту",
    "The title is shown for the first 3 seconds. The music starts softly and fades out at the end; a short song is repeated. "
    "Changing music or title later makes a new version quickly, without a new analysis.":
        "Надпись видна первые 3 секунды. Музыка начинается плавно и затихает в конце; короткая песня повторяется. "
        "Если потом поменять музыку или надпись, новая версия соберётся быстро, без нового анализа.",
    "No music chosen. You can also paste the path.": "Музыка не выбрана. Можно вставить путь к файлу.",
    "the title could not be drawn: no suitable font on this PC": "надпись не нарисована: на этом компьютере нет подходящего шрифта",
    "emoji and symbols the font cannot draw were left out of the title": "эмодзи и значки, которых нет в шрифте, в надпись не вошли",
    "What AI+ saw in your videos (kept for every reel, so the same video is never looked at twice): ":
        "Что ИИ+ увидел в твоих видео (хранится для всех роликов, чтобы одно видео не просматривать дважды): ",
    "What the AI found in your videos and the cut moments (kept for every reel, so the same video is never analysed twice): ":
        "Что ИИ нашёл в твоих видео и нарезанные моменты (хранится для всех роликов, чтобы одно видео не анализировать дважды): ",
    "Free": "Освободить", "Freed.": "Освобождено.",
    "AI+ is being prepared for the Library: stop it on the Library page first": "Сейчас идёт подготовка ИИ+ для Библиотеки: сначала останови её на странице Библиотеки",
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
    "joining segments and verifying": "склеиваю куски и проверяю",
    "joining segments again (the encoder stood still)": "склеиваю куски ещё раз (кодировщик остановился)", "choosing moments": "выбираю моменты",
    "analysing videos": "анализирую видео", "measuring the moments": "оцениваю моменты", "cutting the pieces": "нарезаю куски", "prepared": "подготовлено",
    "The videos have no useful sound - a reel with your own music?": "В видео нет полезного звука — ролик со своей музыкой?",
    "Add music…": "Добавить музыку…", "technical analysis": "технический анализ",
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
    "Save MP4": "Сохранить MP4", "Save to another folder…": "Сохранить в другую папку…",
    "The same reel with the original sound": "Тот же ролик с исходным звуком",
    "Building the test reel…": "Собираю тестовый ролик…",
    "Delete this project and all its versions for good? Saved MP4 files and your original videos stay.": "Удалить этот проект и все его версии навсегда? Сохранённые MP4 и твои исходные видео останутся.",
    "Saved MP4 files and your original videos stay": "Сохранённые MP4 и исходные видео останутся",
    "Project deleted. Freed:": "Проект удалён. Освобождено:",
    "Delete": "Удалить",
    "Analysis and render caches of all projects (versions and saved MP4 stay; the next build of a project analyses again):": "Кэш анализа и сборки всех проектов (версии и сохранённые MP4 останутся; следующая сборка проекта заново проанализирует видео):",
    "Analysis and render caches of all projects (versions and saved MP4 stay; the next build of a project makes them again):": "Кэш анализа и сборки всех проектов (версии и сохранённые MP4 останутся; следующая сборка проекта сделает его заново):",
    "Freed:": "Освобождено:",
    "Small copy for messengers": "Маленькая копия для мессенджеров", "About 720p, a much smaller file": "Около 720p, файл намного меньше",
    "Small copy saved:": "Маленькая копия сохранена:",
    "New in this version": "Новое в этой версии",
    "Find a project": "Найти проект",
    "Recent folders:": "Недавние папки:",
    "Use this version": "Перейти на эту версию", "Projects stay the same": "Проекты останутся те же",
    "Switching to another version…": "Переключаюсь на другую версию…",
    "This MediaEngine closes and the other version starts. This page opens it by itself.": "Этот MediaEngine закроется, и запустится другая версия. Страница откроет её сама.",
    "The other version did not start. Start it from its folder:": "Другая версия не запустилась. Запусти её из её папки:",
    "That version is not on this PC.": "Этой версии нет на компьютере.",
    "A reel is being made. Switch when it is ready.": "Сейчас собирается ролик. Переключись, когда он будет готов.",
    "Only on Windows.": "Только в Windows.",
    "That version is too old to switch to from here. Start it from its folder.": "На эту версию отсюда не переключиться (она слишком старая). Запусти её из её папки.",
    "A Library task is running (see Activity). Switch when it has finished.": "Идёт задача Библиотеки (см. «Активность»). Переключись, когда она закончится.",
    "The AI+ model is being downloaded. Switch when it is done.": "Скачивается модель ИИ+. Переключись, когда закончится.",
    "AI+ is being prepared for the Library. Stop it first (it continues next time).": "Идёт подготовка ИИ+ для Библиотеки. Сначала останови её (потом она продолжится).",
    "The file of this version changed on disk; build the version again": "Файл этой версии изменился на диске; собери версию заново",
    "Videos folder": "Папка с видео", "Open the folder of the videos in Explorer": "Открыть папку с видео в проводнике",
    "“Save MP4” in one step on any version (no separate Accept).": "«Сохранить MP4» одной кнопкой у любой версии (без отдельного «Принять»).",
    "A reel for every day of a trip: open a big folder, “A reel for every day”.": "Ролик на каждый день поездки: открой большую папку → «Ролик на каждый день».",
    "Vertical reel from horizontal videos: the whole picture with blurred edges, if you like.": "Вертикальный ролик из горизонтальных видео: по желанию кадр целиком, края размыты.",
    "“Small copy for messengers” next to Save MP4.": "«Маленькая копия для мессенджеров» рядом с «Сохранить MP4».",
    "Library: select videos and press “Make a reel”.": "Библиотека: отметь видео и нажми «Сделать ролик».",
    "Reels up to 2 minutes; the new reel starts with your last settings.": "Ролики до 2 минут; новый ролик начинается с твоих прошлых настроек.",
    "A reel being made is shown at the top of every page.": "Ролик, который собирается, виден вверху каждой страницы.",
    "AI mode is faster with big videos (4K): several videos are analysed at once, moments are cut quicker.": "ИИ-режим быстрее с большими видео (4K): несколько видео анализируются одновременно, моменты нарезаются быстрее.",
    "A new reel from videos that were already analysed (another project, a reel for every day) analyses and cuts nothing again.":
        "Новый ролик из уже проанализированных видео (другой проект, ролик на каждый день) ничего не анализирует и не нарезает заново.",
    "While moments are being found: about how many minutes are left.": "Во время поиска моментов видно, сколько примерно минут осталось.",
    "A Windows notification when a reel that took more than a minute is ready (can be turned off in Settings).":
        "Уведомление Windows, когда готов ролик, который собирался дольше минуты (выключается в Настройках).",
    "AI with 4K videos is faster again: moments are looked at in small copies, the reel is cut from the originals.":
        "ИИ с 4K-видео стал ещё быстрее: моменты оцениваются по уменьшенным копиям, а ролик режется из оригиналов.",
    "“Prepare in advance” on the new-reel page: the videos are analysed now (for example overnight), the reel is then made in minutes.":
        "«Подготовить заранее» на странице нового ролика: видео анализируются сразу (например, ночью), потом ролик собирается за минуты.",
    "AI+ theme “Aerial view (drone)”: the view from above, without take-off and landing on the ground.":
        "Тема ИИ+ «Вид сверху (дрон)»: вид с высоты, без взлёта и посадки на земле.",
    "Check this PC can test the graphics card: if it decodes 4K faster with exactly the same picture, the videos are cut with it.":
        "«Проверка компьютера» умеет проверить видеокарту: если она разбирает 4K быстрее и с точно такой же картинкой, видео режутся ею.",
    "Choosing the moments of a new reel length uses several processor cores (the same choice, found faster).":
        "Выбор моментов для новой длины ролика идёт на нескольких ядрах процессора (выбор тот же, только быстрее).",
    "“Prepare in advance” for a reel for every day of a big folder too.":
        "«Подготовить заранее» теперь есть и для роликов на каждый день большой папки.",
    "Vertical HD": "Вертикально HD",
    "A reel for every day": "Ролик на каждый день",
    "One reel for each of these days, made one after another:": "По ролику на каждый из этих дней, по очереди:",
    "No day with videos to use.": "Нет дней с видео для ролика.",
    "More than 31 days: choose the days one by one.": "Больше 31 дня: выбери дни по одному.",
    "The day is taken from the file name (e.g. VID_20260714_…), otherwise from the recording time in the video, otherwise from the file's date.": "День берётся из имени файла (например, VID_20260714_…), иначе из времени записи в самом видео, иначе из даты файла.",
    "Horizontal videos in a vertical reel:": "Горизонтальные видео в вертикальном ролике:",
    "Fill the screen (cropped to the interesting part)": "На весь экран (обрезать до главного)",
    "Whole picture, blurred edges": "Кадр целиком, края размыты",
    "blurred edges": "края размыты",
    "Unknown framing": "Неизвестное кадрирование",
    "Archive the project first": "Сначала отправь проект в архив",
    "A video of this project is open (in a player?). Close it and try again.": "Видео этого проекта открыто (в плеере?). Закрой его и попробуй ещё раз.",
    "Reels are made one at a time. This one starts when this reel is ready:": "Ролики делаются по одному. Этот начнётся, когда будет готов этот ролик:",
    "Up to a few minutes. You can leave this page: the result is shown here when it is ready.": "До нескольких минут. Можно уйти с этой страницы: результат появится здесь, когда будет готов.",
    "Mark it as the chosen version without saving a file": "Отметить как выбранную версию, не сохраняя файл",
    "Exported": "Экспортировано", "Compare blind with": "Сравнить вслепую с", "Compare": "Сравнить",
    "Make a variant": "Сделать вариант", "Make variant": "Сделать вариант", "Build reel": "Собрать ролик", "Build": "Собрать",
    "The current revision stays as it is. It keeps its removed moments and your edits; changing only format or sound reuses the analysis.":
        "Текущая версия не меняется. Убранные моменты и правки сохраняются; смена только формата или звука использует готовый анализ.",
    "Revisions": "Версии", "accepted": "принята", "viewing": "открыта", "edited by you": "твои правки", "excluded": "убрано",
    "Revision": "Версия", "sound": "звук", "Technical only (no AI)": "Только техника (без ИИ)", "AI moments (FAST_LOCAL)": "ИИ-моменты (FAST_LOCAL)",
    "Auto → original sound": "Авто → звук исходника",
    "Auto → muted (some moments have no sound; choose “Source sound” to keep the sound)":
        "Авто → без звука (в части моментов нет звука; выбери «Звук исходника», чтобы оставить звук)",
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
    "You can close this window: the reel keeps building and the PC does not go to sleep. When it is ready, Windows shows a notification - click it to see the reel.":
        "Окно можно закрыть: ролик продолжит собираться, а компьютер не уснёт. Когда он будет готов, Windows покажет уведомление — нажми на него, чтобы посмотреть.",
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
    "(can be freed; the next build makes it again - what the AI found in the videos is kept for every project)": "(можно очистить; следующая сборка сделает его заново — найденное ИИ в видео хранится для всех проектов)",
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
    "Horizontal 960×540": "Горизонтально 960×540",
    "Vertical Full HD 1080×1920 (phone, Reels, Shorts)": "Вертикально Full HD 1080×1920 (телефон, Reels, Shorts)",
    "Vertical small 540×960 (quick to send)": "Вертикально, маленький 540×960 (быстро отправить)",
    "Vertical small": "Вертикально, маленький", "Horizontal small": "Горизонтально, маленький",
    "Horizontal small 960×540 (quick to send)": "Горизонтально, маленький 960×540 (быстро отправить)",
    "Horizontal Full HD 1920×1080 (TV, YouTube)": "Горизонтально 1920×1080 (телевизор, YouTube)", "Horizontal HD": "Горизонтально HD", " · recommended": " · рекомендуется", ", total ": ", всего ",
    "Only ": "Всего ", "Without it MediaEngine can only use the ": "Без неё MediaEngine умеет только режим ",
    " selection (sharpness, motion, exposure); it does not understand what happens in the video.":
        " (резкость, движение, свет); что происходит в кадре, он не понимает.",
    "Without it reels use the clearly labelled ": "Без неё ролики собираются в явно отмеченном режиме ",
    "The AI model is not downloaded yet": "Модель ИИ ещё не скачана", "AI model is installed": "Модель ИИ установлена",
    "Download the AI model": "Скачать модель ИИ",
    "Without it reels use the clearly labelled": "Без неё ролики собираются в явно отмеченном режиме",
    "selection (sharpness, motion, light). Download once: 30 MB from huggingface.co (free); it is kept in MediaEngine's own folder and every file is checked.":
        "(резкость, движение, свет). Скачивается один раз: 30 МБ с huggingface.co (бесплатно), хранится в папке MediaEngine, каждый файл проверяется.",
    "not downloaded yet - 'Download the AI model' below (30 MB); until then only 'Technical only' reels":
        "ещё не скачана — кнопка «Скачать модель ИИ» ниже (30 МБ); до этого только ролики «Только техника»",
    "files changed or incomplete - not used; download the AI model again below":
        "файлы изменены или неполные — не используется; скачай модель ИИ ещё раз ниже",
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
    "The archive folder must be a full folder path, such as": "Папка архива должна быть полным путём, например",
    "A composition is being rendered (Composer). Switch when it is ready.": "Идёт сборка композиции (Composer). Переключись, когда она будет готова.",
    "A composition is being rendered (Composer)": "Идёт сборка композиции (Composer)",
    "Waiting for the test on Check this PC to finish": "Ждёт окончания проверки на странице «Проверка компьютера»",
    "more values than columns (put a number like 1,234 in quotes or write 1234)": "значений больше, чем столбцов (число вида 1,234 возьми в кавычки или напиши 1234)",
    "fewer values than columns": "значений меньше, чем столбцов",
    "Remove from queue": "Убрать из очереди",
    "The source videos are not available (card or drive disconnected?). Plug it in and press Retry.":
        "Исходные видео недоступны (карта или диск отключены?). Подключи и нажми «Повторить».",
    "The source folder is not available (card or drive disconnected?). Plug it in and press Retry.":
        "Папка с видео недоступна (карта или диск отключены?). Подключи и нажми «Повторить».",
    "The test reel of Check this PC is being made. Wait until it is ready.": "Делается тестовый ролик «Проверки компьютера». Подожди, пока он будет готов.",
    "The graphics card is being tested (Check this PC). Wait until the test has finished.": "Идёт проверка видеокарты («Проверка компьютера»). Подожди окончания проверки.",
    "Private and Rejected media cannot be used in a reel": "Видео из Private и Rejected нельзя использовать в ролике",
    "Accept a revision before exporting": "Сначала прими версию (Accept), потом экспорт",
    "This page can only be opened from MediaEngine itself.": "Эту страницу можно открыть только из самого MediaEngine.",
    "Network folders can only be opened from MediaEngine itself: paste the path on the Auto Edit page.":
        "Сетевые папки открываются только из самого MediaEngine: вставь путь на странице «Автомонтаж».",
    "No video of this theme is on this PC now.": "Сейчас на этом компьютере нет видео на эту тему.",
    # "Prepare in advance" (analysis only; the reel later in minutes)
    # decoding on the graphics card (Check this PC)
    "Graphics card": "Видеокарта", "Video decoding on the graphics card": "Разбор видео на видеокарте", "cut with the graphics card": "нарезано видеокартой",
    "not tested yet - press 'Test the graphics card' below (about a minute, your videos are not used)":
        "ещё не проверено — нажми «Проверить видеокарту» ниже (около минуты, твои видео не используются)",
    "Testing the graphics card…": "Проверяю видеокарту…", "About a minute or two. You can leave this page.": "Минуту-две. Страницу можно закрыть.",
    "The test cuts short 4K test clips with the processor and with the graphics card and compares every frame. The graphics card is used only if the picture is exactly the same and it is clearly faster. Your videos are not used.":
        "Проверка режет короткие тестовые 4K-клипы процессором и видеокартой и сравнивает каждый кадр. Видеокарта используется, только если картинка точно такая же и это заметно быстрее. Твои видео не используются.",
    "Test again": "Проверить ещё раз", "Test the graphics card": "Проверить видеокарту",
    "Use the graphics card": "Использовать видеокарту", "Do not use the graphics card": "Не использовать видеокарту",
    "turned off": "выключено", "· tested ": "· проверено ",
    "not used: this FFmpeg cannot decode video on a graphics card": "не используется: этот FFmpeg не умеет разбирать видео на видеокарте",
    "not used: the graphics card cannot decode these videos here": "не используется: видеокарта здесь не разбирает такие видео",
    "not used: the picture is not exactly the same as the processor's": "не используется: картинка не точно такая же, как у процессора",
    "making 4K test clips": "делаю тестовые 4K-клипы", "processor": "процессор",
    "not used: the test could not be finished - test again": "не используется: проверка не закончилась — проверь ещё раз",
    "not used: FFmpeg or the graphics driver changed since the test - test again":
        "не используется: после проверки сменился FFmpeg или драйвер видеокарты — проверь ещё раз",
    "Prepare in advance": "Подготовить заранее", "Preparing in advance": "Подготовка заранее",
    "Prepare in advance: the videos of every day are only analysed now (for example overnight); each day's reel is then made in minutes.":
        "Подготовить заранее: видео каждого дня сейчас только анализируются (например, ночью); потом ролик каждого дня собирается за минуты.",
    "Preparing failed": "Подготовка не удалась", "Preparing cancelled": "Подготовка отменена",
    "Moments: AI": "Моменты: ИИ", "Moments: AI+": "Моменты: ИИ+", "Moments: Technical only": "Моменты: только техника",
    "Prepared in advance": "Подготовлено заранее", "Prepared": "Подготовлено", "PREPARED": "ПОДГОТОВЛЕН",
    "Prepare in advance: MediaEngine only analyses the videos now - for example overnight. The reel is then made from them in minutes.":
        "Подготовить заранее: MediaEngine сейчас только анализирует видео — например, ночью. Потом ролик из них собирается за минуты.",
    "You can close this window: the videos keep being analysed and the PC does not go to sleep. When it is done, Windows shows a notification and the reel is made here in minutes.":
        "Окно можно закрыть: анализ продолжится, компьютер не уснёт. Когда закончится, Windows покажет уведомление, а ролик здесь соберётся за минуты.",
    "You can close this window: the videos keep being analysed and the PC does not go to sleep. When it is done, the reel is made here in minutes.":
        "Окно можно закрыть: анализ продолжится, компьютер не уснёт. Когда закончится, ролик здесь соберётся за минуты.",
    "Videos analysed:": "Проанализировано видео:", "skipped:": "пропущено:", "took": "заняло",
    "Now press Build: the reel is made from the prepared videos in minutes. Videos added to the folder later are analysed during the build.":
        "Теперь нажми «Собрать»: ролик из подготовленных видео соберётся за минуты. Видео, добавленные в папку позже, проанализируются во время сборки.",
    # orders from other programs (orders.py, orders_web.py)
    "Orders": "Заказы", "Reel from videos": "Ролик из видео", "Video by plan": "Видео по плану", "ordered by": "заказчик:",
    "Other programs on this PC can order a video: they put an order into the Inbox folder, MediaEngine makes the video and puts it into Done with a receipt. Nothing is published.":
        "Другие программы на этом компьютере могут заказать видео: они кладут заказ в папку «Входящие» (Inbox), MediaEngine делает видео и кладёт его в папку «Готово» (Done) вместе с квитанцией. Ничего не публикуется.",
    "Inbox folder": "Папка «Входящие»", "Done folder": "Папка «Готово»",
    "Delete this order's folders in Orders (with the files it brought)? Your own videos elsewhere and your projects stay.":
        "Удалить папки этого заказа (вместе с файлами, которые он принёс)? Твои видео в других папках и проекты останутся.",
    "Reject this order? It will not be done.": "Отклонить заказ? Он не будет выполнен.", "Stop this order?": "Остановить заказ?",
    "Orders in work": "В работе", "New orders": "Новые заказы", "Orders not done": "Не выполнены", "Ready orders": "Готовые заказы",
    "No orders yet. When another program puts an order into the Inbox folder, it appears here.":
        "Заказов пока нет. Когда другая программа положит заказ в папку «Входящие», он появится здесь.",
    "Start at once": "Выполнять сразу", "Wait for my OK": "Ждать моего OK", "Save setting": "Сохранить",
    "How another program sends an order": "Как другая программа присылает заказ",
    "It makes a folder in Inbox (the folder name is the order's name), puts its files there and writes order.json last. MediaEngine takes the order, makes the video and puts the answer into Done (video.mp4 and result.json) or into Failed (result.json with the reason). Nothing is published or sent anywhere. The full format: ORDERS.md in the Orders folder.":
        "Она создаёт папку во «Входящих» (имя папки — номер заказа), кладёт туда свои файлы и последним — файл заказа. MediaEngine берёт заказ, делает видео и кладёт ответ в «Готово» (видео и квитанцию) или в «Не выполнены» (Failed, квитанцию с причиной). Ничего не публикуется и никуда не отправляется. Полный формат описан в файле ORDERS.md в папке Orders.",
    "A video by plan (pictures, pieces of videos and a sound track):": "Видео по плану (картинки, куски видео и звуковая дорожка):",
    "A reel from videos (MediaEngine chooses the moments):": "Ролик из видео (моменты выбирает MediaEngine):",
    "Working on it": "Делаю", "Waiting for its turn": "Ждёт очереди", "Open project": "Открыть проект",
    "Run": "Выполнить", "Reject": "Отклонить", "Waiting for your OK": "Ждёт твоего OK", "Starts in a moment": "Сейчас начнётся",
    "Still arriving (order.json is not there yet)": "Ещё приходит (файла заказа пока нет)",
    "Try again": "Повторить", "Run again": "Выполнить снова", "video ready": "видео готово",
    "The order could not be done.": "Заказ не удалось выполнить.",
    "The order file is not valid JSON.": "Файл заказа — не правильный JSON.",
    "A file named in the order is not there.": "Файла, указанного в заказе, нет.",
    "The order is not in the MediaEngine order format.": "Заказ не в формате заказов MediaEngine.",
    "MediaEngine does not know this kind of order.": "MediaEngine не знает такого вида заказа.",
    "Something in the order is wrong.": "В заказе что-то указано неправильно.",
    "The order points to a file outside its folder.": "Заказ ссылается на файл вне своей папки.",
    "The order points to a network folder: not used.": "Заказ ссылается на сетевую папку — она не используется.",
    "The order's name is not allowed.": "Такое имя заказа нельзя.",
    "An order with this name was already received.": "Заказ с таким именем уже был.",
    "The times in the plan do not fit together.": "Времена в плане не стыкуются.",
    "The plan is longer than 10 minutes.": "План длиннее 10 минут.",
    "The plan has too many clips.": "В плане слишком много клипов.",
    "A picture of the plan cannot be read.": "Картинку из плана не прочитать.",
    "A video of the plan cannot be read.": "Видео из плана не прочитать.",
    "The sound of the plan cannot be read.": "Звук из плана не прочитать.",
    "The video could not be made.": "Видео не получилось сделать.",
    "The finished video did not pass its checks.": "Готовое видео не прошло проверку.",
    "The finished video could not be copied (disk full?).": "Готовое видео не скопировалось (диск полон?).",
    "The videos of the order cannot be used.": "Видео из заказа нельзя использовать.",
    "No video of this theme is on this PC.": "Видео на эту тему на компьютере нет.",
    "The AI+ model is not on this PC yet.": "Модели ИИ+ на компьютере пока нет.",
    "The reel could not be started.": "Ролик не удалось запустить.",
    "You rejected this order.": "Ты отклонил этот заказ.", "You stopped this order.": "Ты остановил этот заказ.",
    "MediaEngine had an internal error with this order.": "Внутренняя ошибка MediaEngine с этим заказом.",
    "This order was started several times and never finished (MediaEngine was closed each time).":
        "Этот заказ запускался несколько раз и ни разу не закончился (MediaEngine каждый раз закрывали).",
    "A picture of the plan is too big.": "Картинка из плана слишком большая.",
    # found by the QA review (2026-10-17): messages that stayed English
    "The source folder is not available (disconnected drive?)": "Папка с исходными видео недоступна (диск отключён?)",
    "The source videos are not available (disconnected drive?)": "Исходные видео недоступны (диск отключён?)",
    "Keep at least one moment.": "Оставь хотя бы один момент.",
    "The program took the answer.": "Программа забрала ответ.",
    "another video has the same name and there was no room on the drive to analyse it apart":
        "у другого видео такое же имя, а на диске не хватило места, чтобы проанализировать его отдельно",
    "Free it? Every video is then analysed again - for a reel, for videos prepared in advance and for AI+ in the Library (that can take hours for a big Library).":
        "Освободить? Тогда каждое видео будет анализироваться заново — для ролика, для подготовленных заранее видео и для ИИ+ в Библиотеке (для большой Библиотеки это часы).", "Could not apply the edits: ": "Не удалось применить правки: ",
    "The exported file is not available any more: ": "Сохранённого файла больше нет: ", "Job not found": "Сборка не найдена",
    "Export not found": "Сохранение не найдено", "not found (moved or deleted)": "не найден (перемещён или удалён)",
    "A video of this reel was marked Private while the reel was being built, so the reel was not kept. Press Retry (for a version edited by hand: Let MediaEngine choose again): it is made without that video.":
        "Пока ролик собирался, одно из его видео отметили как личное, поэтому ролик не сохранён. Нажми «Повторить» (для версии, которую ты правил вручную, — «Пусть MediaEngine выберет заново»): он соберётся без этого видео.",
    "This version contains a video that is marked Private now. Make a new version (Let MediaEngine choose again, or a variant): it is made without that video.":
        "В этой версии есть видео, которое теперь отмечено как личное. Сделай новую версию («Пусть MediaEngine выберет заново» или вариант): она будет без этого видео.",
    "This folder has more than 64 videos now. Make a new reel from it (Auto Edit → New reel): you can pick a day or the videos there.":
        "В этой папке теперь больше 64 видео. Сделай из неё новый ролик (Автомонтаж → Новый ролик): там можно выбрать день или сами видео.",
    "An order from another program is being done (Auto Edit → Orders)": "Выполняется заказ другой программы (Автомонтаж → Заказы)",
    "An order from another program is being done. Switch when it is ready.": "Выполняется заказ другой программы. Переключись, когда он будет готов.",
    "Order not found": "Заказ не найден", "This order cannot be done again.": "Этот заказ нельзя выполнить снова.",
    "This order cannot be deleted now.": "Этот заказ сейчас нельзя удалить.",
    "The video of this order is not there.": "Видео этого заказа нет.", "The folder of this order is not there.": "Папки этого заказа нет.",
    "Orders from other programs: a program puts an order into the Inbox folder (Auto Edit → Orders), MediaEngine makes the video and puts it into Done.":
        "Заказы от других программ: программа кладёт заказ в папку «Входящие» (Автомонтаж → Заказы), MediaEngine делает видео и кладёт его в «Готово».",
    # tray icon, switch without a question, the Update button (2026-10-17/18)
    "MediaEngine is in the tray (next to the clock): click it to open the window, right-click → Quit to close the program.":
        "MediaEngine в трее (рядом с часами): щелчок открывает окно, правая кнопка → «Выход» закрывает программу.",
    "A new version takes over from the old one by itself, without the “switch?” question.":
        "Новая версия сама сменяет старую, без вопроса «переключиться?».",
    "The “Update” button at the top: MediaEngine finds a newer version on GitHub and installs it itself (only when you press it).":
        "Кнопка «Обновить» вверху: MediaEngine сам находит новую версию на GitHub и ставит её (только когда ты её нажмёшь).",
    "Update": "Обновить", "Updates": "Обновления", "Look for a newer MediaEngine on GitHub": "Найти новую версию MediaEngine на GitHub",
    "Check for updates": "Проверить обновления", "Updating to": "Обновление до", "This version:": "Эта версия:",
    "Downloading the new version…": "Скачиваю новую версию…", "Putting the new version next to this one…": "Ставлю новую версию рядом с этой…",
    "Starting the new version…": "Запускаю новую версию…",
    "Do not close this window: MediaEngine restarts by itself and this page then opens the new version.":
        "Не закрывай это окно: MediaEngine перезапустится сам, и эта страница откроет новую версию.",
    "The new version is taking long to start. If nothing happens, start MediaEngine from the desktop shortcut.":
        "Новая версия долго запускается. Если ничего не происходит, запусти MediaEngine ярлыком на рабочем столе.",
    "This is the newest version.": "Это самая новая версия.", "Open the page with the installer": "Открыть страницу с установщиком",
    "A newer version is ready:": "Есть новая версия:", "What is new": "Что нового", "Download:": "Загрузка:", "Update now": "Обновить сейчас",
    "This time it needs the full installer: Python or its libraries changed. Download its Setup and install it (projects stay the same).":
        "В этот раз нужен полный установщик: изменился Python или его библиотеки. Скачай Setup и установи его (проекты останутся те же).",
    "It goes into a new folder next to this one; this version stays on the PC (to go back: Check this PC). Projects stay the same. MediaEngine restarts by itself.":
        "Новая версия ставится в новую папку рядом с этой; эта остаётся на компьютере (вернуться: «Проверка компьютера»). Проекты те же. MediaEngine перезапустится сам.",
    "MediaEngine looks for a newer version on GitHub only when you press this button; it goes online for nothing else.":
        "MediaEngine ищет новую версию на GitHub, только когда ты нажимаешь эту кнопку; больше он ни за чем в интернет не выходит.",
    "Updates are turned off here.": "Обновления здесь выключены.",
    "Only an installed MediaEngine (Setup or ZIP) updates itself.": "Сам обновляется только установленный MediaEngine (Setup или ZIP).",
    "This version cannot update itself yet. Install the new version once with its Setup.":
        "Эта версия ещё не умеет обновляться сама. Один раз установи новую версию её установщиком (Setup).",
    "MEDIAENGINE_UPDATE_URL may only point at this PC (it is for checks).": "MEDIAENGINE_UPDATE_URL может указывать только на этот компьютер (это для проверок).",
    "The update description on GitHub is damaged. Try again later.": "Описание обновления на GitHub повреждено. Попробуй позже.",
    "This version does not understand the new update. Install the new version once with its Setup.":
        "Эта версия не понимает новое обновление. Один раз установи новую версию её установщиком (Setup).",
    "An update is being installed right now.": "Обновление уже устанавливается.",
    "No update has been published yet.": "Обновлений пока не выложено.",
    "GitHub answered with an error. Try again later.": "GitHub ответил ошибкой. Попробуй позже.",
    "No connection to GitHub. Check the internet connection and try again.": "Нет связи с GitHub. Проверь интернет и попробуй снова.",
    "Press Check for updates first.": "Сначала нажми «Проверить обновления».",
    "This is already the newest version.": "Это уже самая новая версия.",
    "This update needs the full installer this time (Python or its libraries changed).":
        "Для этого обновления нужен полный установщик (изменился Python или его библиотеки).",
    "The update could not be installed.": "Обновление не удалось установить.",
    "Not enough free space on the disk with MediaEngine for the update.": "Для обновления не хватает места на диске с MediaEngine.",
    "The download is bigger than announced, so it is not used.": "Загрузка больше заявленной, поэтому не используется.",
    "A newer version was published in the meantime. Press Check for updates again.":
        "Пока шла загрузка, вышла ещё более новая версия. Нажми «Проверить обновления» ещё раз.",
    "The download was interrupted. Check the internet connection and try again.": "Загрузка прервалась. Проверь интернет и попробуй снова.",
    "The downloaded file is damaged (its checksum differs), so it is not used. Try again.":
        "Скачанный файл повреждён (контрольная сумма не совпадает), поэтому не используется. Попробуй снова.",
    "A folder with the new version's name is already there, but it is not a complete MediaEngine. Remove that folder or install the new version with its Setup.":
        "Папка с именем новой версии уже есть, но это не полный MediaEngine. Удали эту папку или установи новую версию её установщиком (Setup).",
    "The update contains a file outside its folder, so it is not used.": "В обновлении есть файл вне его папки, поэтому оно не используется.",
    "The update is much bigger than expected, so it is not used.": "Обновление намного больше ожидаемого, поэтому не используется.",
    "The update is incomplete, so it is not used.": "Обновление неполное, поэтому не используется.",
    "The update is for another kind of MediaEngine, so it is not used.": "Обновление для другого вида MediaEngine, поэтому не используется.",
    "An update is being installed. Wait a minute.": "Устанавливается обновление. Подожди минуту.",
    "Type the full path of the folder first.": "Сначала впиши полный путь к папке.", "MB": "МБ",
    "in Library (the file stays in its folder)": "в Библиотеке (файл остаётся в своей папке)",
    "Online AI": "Онлайн-ИИ", "A new version goes next to this one.": "Новая версия ставится рядом с этой.",
    "The Update button looks on GitHub for a newer version only when you press it. The new version goes into its own folder and the previous one stays, so you can go back to it on Check this PC. If a new version does not start, the previous one is started again.":
        "Кнопка «Обновить» ищет новую версию на GitHub, только когда ты её нажимаешь. Новая версия ставится в свою папку, а прежняя остаётся — к ней можно вернуться на странице «Проверка компьютера». Если новая версия не запустится, снова запускается прежняя.",
    "No connection to huggingface.co. Check the internet connection and try again, or copy the model from another PC (Copy from a folder…).":
        "Нет связи с huggingface.co. Проверь интернет и попробуй снова или скопируй модель с другого компьютера («Скопировать из папки…»).",
    "The source videos are not available: the drive is disconnected, or the folder was moved, renamed or deleted. Versions and saved MP4 files are kept; new builds are possible when the videos are back in their place:":
        "Исходные видео недоступны: диск отключён или папку переместили, переименовали или удалили. Версии и сохранённые MP4 на месте; новые сборки — когда видео вернутся на своё место:",
    "Works; the AI model is not downloaded yet (Check this PC)": "Работает; модель ИИ ещё не скачана («Проверка компьютера»)",
    "Cannot tell whether work is running.": "Не удалось понять, идёт ли работа.",
    "Start at sign-in could not be changed.": "Не удалось изменить запуск при входе в Windows.",
    "A reel being made when the PC restarts (or MediaEngine stops without Quit) is made again by itself at the next start, once.":
        "Ролик, который собирался, когда компьютер перезагрузился (или MediaEngine закрылся не через «Выход»), сам собирается заново при следующем запуске — один раз.",
    "Stopped when MediaEngine stopped unexpectedly (for example a restart of the PC). It is made again by itself.":
        "Остановлен, когда MediaEngine неожиданно закрылся (например, при перезагрузке компьютера). Собирается заново сам.",
    "Settings: start MediaEngine in the background when you sign in to Windows (off unless you turn it on); reels waiting from before a restart go on.":
        "Настройки: запуск MediaEngine в фоне при входе в Windows (выключен, пока ты сам не включишь); ролики, ждавшие до перезагрузки, продолжатся.",
    "Start MediaEngine in the background when I sign in to Windows (icon in the tray; reels waiting from before a restart go on)":
        "Запускать MediaEngine в фоне при входе в Windows (значок в трее; ролики, ждавшие до перезагрузки, продолжатся)",
    "Work started in the meantime. The new version is ready: press Update now again when the work has finished.":
        "Тем временем началась работа. Новая версия готова: нажми «Обновить сейчас» ещё раз, когда работа закончится.",
    "The new version is ready in its folder, but it did not take over. Press Update now to try again.":
        "Новая версия готова в своей папке, но не запустилась вместо этой. Нажми «Обновить сейчас», чтобы попробовать снова.",
    "The new version did not start, so this version is running again. Details for support are in the logs folder.":
        "Новая версия не запустилась, поэтому снова работает эта. Подробности для поддержки — в папке logs.",
    # voice-over and captions (voice.py, voice_web.py)
    "Voice-over": "Озвучка", "Voice-over · MediaEngine": "Озвучка · MediaEngine",
    "A text read by a voice, with captions timed to the words; captions and text for your own videos.":
        "Текст, прочитанный голосом, и субтитры точно по словам; субтитры и текст для твоих видео.",
    "Installing the voice add-on": "Устанавливается модуль озвучки",
    "Checking the PC…": "Проверяю компьютер…",
    "Downloading and installing the add-on's Python parts (about 3 GB)…": "Скачиваю и ставлю части модуля для Python (около 3 ГБ)…",
    "Downloading the voice models (about 5 GB)…": "Скачиваю голосовые модели (около 5 ГБ)…",
    "Starting the add-on for a test…": "Пробный запуск модуля…",
    "This takes from a few minutes to an hour, depending on the internet. You can use MediaEngine meanwhile; closing it stops the installation (it continues where it stopped when you press Install again).":
        "Это займёт от нескольких минут до часа — смотря какой интернет. MediaEngine пока можно пользоваться; если закрыть его, "
        "установка остановится (и продолжится с того же места, когда снова нажмёшь «Установить»).",
    "The voice add-on is installed.": "Модуль озвучки установлен.", "It works on": "Работает на",
    "the graphics card": "видеокарте", "the processor (slow)": "процессоре (медленно)", "the processor": "процессоре",
    "Size:": "Размер:", "Remove the add-on": "Удалить модуль",
    "Frees the disk space. The voice-overs and videos made with it stay.": "Освобождает место на диске. Сделанные озвучки и видео останутся.",
    "Remove the voice add-on?": "Удалить модуль озвучки?",
    "Graphics card:": "Видеокарта:", "— the voice is made on it (fast).": "— голос делается на ней (быстро).",
    "No NVIDIA graphics card was found: the voice is made on the processor (slow: about a minute for every sentence).":
        "Видеокарта NVIDIA не найдена: голос будет делаться на процессоре (медленно: около минуты на каждое предложение).",
    "Install the voice add-on": "Установить модуль озвучки",
    "This MediaEngine uses another Python: install the add-on again.": "Этот MediaEngine работает на другом Python: установи модуль заново.",
    "The voice add-on is not installed.": "Модуль озвучки не установлен.",
    "It is downloaded once: about 13 GB (the add-on's Python parts and three models: Qwen3-TTS for the voices from a recording, the voice 9_2 too; VoxCPM2 for a voice from a description; Whisper for checking the words and for captions). It goes into the data folder:":
        "Он скачивается один раз: около 13 ГБ (части для Python и три модели: Qwen3-TTS — голоса из записи, в том числе голос 9_2; "
        "VoxCPM2 — голос по описанию; Whisper — проверка слов и субтитры). Он ставится в папку данных:",
    "MediaEngine goes online for it only when you press the button (pypi.org, download.pytorch.org, huggingface.co). Free and open models; nothing is sent anywhere.":
        "MediaEngine выходит в интернет для этого только по нажатию кнопки (pypi.org, download.pytorch.org, huggingface.co). "
        "Модели бесплатные и открытые; никуда ничего не отправляется.",
    "Free space there:": "Свободно там:",
    "Not enough free space: about 26 GB are needed while installing.": "Мало свободного места: на время установки нужно около 26 ГБ.",
    "New voice-over": "Новая озвучка", "The text to be said…": "Текст, который нужно сказать…",
    "Write it the way it is said: short sentences, commas and dots where the pauses are. Words between *stars* are shown in the color in the captions.":
        "Пиши так, как говорят вслух: короткие фразы, запятые и точки там, где паузы. Слова между *звёздочками* в субтитрах будут цветными.",
    "Write it the way it is said: short sentences, commas and dots where the pauses are.":
        "Пиши так, как говорят вслух: короткие фразы, запятые и точки там, где паузы.",
    "Voice": "Голос",
    "Host - the voice of 9_2": "Ведущая — голос 9_2",
    "The recording of this voice is missing from this version of MediaEngine.": "В этой версии MediaEngine нет записи этого голоса.",
    "The recording of this voice is no longer there (a saved voice deleted, or a voice this version of MediaEngine does not have).":
        "Записи этого голоса больше нет (сохранённый голос удалён или в этой версии MediaEngine такого голоса нет).",
    "My description of a voice (English works best)": "Свой голос по описанию (лучше писать по-английски)",
    "A voice from a recording (a person who agreed to it)": "Голос из записи (человека, который на это согласен)",
    "For example: a calm man in his forties with a deep, warm voice, slow pace":
        "Например: спокойный мужчина лет сорока, низкий тёплый голос, не спеша (по-английски получается лучше)",
    "The recording: 5-30 seconds of one person speaking, e.g. D:\\Voice\\anna.wav":
        "Запись: 5–30 секунд речи одного человека, например D:\\Голос\\anna.wav",
    "Choose…": "Выбрать…",
    "The exact words said in the recording (optional: the voice is copied more closely)":
        "Точные слова из записи (не обязательно: так голос получится ближе)",
    "Use only the voice of a person who agreed to it.": "Используй голос только того человека, который на это согласен.",
    "Language of the text": "Язык текста", "Detect by itself": "Определить автоматически",
    "Make the voice-over": "Сделать озвучку",
    "Captions for a video": "Субтитры для видео",
    "The speech in your video is turned into captions with the words timed to it and burned into a copy of the video. The video itself is only read.":
        "Речь в твоём видео превращается в субтитры точно по словам и вшивается в копию видео. Само видео только читается.",
    "The video, e.g. D:\\Videos\\talk.mp4": "Видео, например D:\\Видео\\разговор.mp4",
    "The video, e.g. D:\\Exports\\reel.mp4": "Видео, например D:\\Экспорт\\ролик.mp4",
    "Language of the speech": "Язык речи", "Captions": "Субтитры",
    "at the bottom": "внизу", "in the middle": "посередине", "at the top": "вверху",
    "Make captions": "Сделать субтитры", "Made": "Сделано",
    "Voice-over on a video": "Озвучка на видео", "Working": "Делается",
    "Interrupted (MediaEngine was closed): it is made again at the next start":
        "Прервано (MediaEngine был закрыт): будет сделано заново при следующем запуске",
    "Starting…": "Запуск…", "Loading the voice model…": "Загружаю голосовую модель…", "Speaking…": "Озвучиваю…",
    "Joining the parts…": "Соединяю части…", "Listening to check every word…": "Слушаю, все ли слова сказаны…",
    "Finishing the sound…": "Довожу звук…", "Reading the sound of the video…": "Читаю звук видео…",
    "Making the video…": "Делаю видео…", "Checking the video…": "Проверяю видео…",
    "Every word was said (checked by listening).": "Все слова сказаны (проверено на слух).",
    "Words not clear when listening:": "Неразборчивых слов:", "of": "из", "made on": "сделано на",
    "Download WAV": "Скачать WAV", "Download captions (SRT)": "Скачать субтитры (SRT)",
    "Put it on a video": "Наложить на видео",
    "Keep the video's own sound (quieter while the voice speaks)": "Оставить звук видео (тише, пока говорит голос)",
    "Captions with the words": "Субтитры со словами", "The voice starts at": "Голос начинается на",
    "Make the video": "Сделать видео", "checked: plays to the end": "проверено: проигрывается до конца",
    "Delete it?": "Удалить?", "Saved:": "Сохранено:",
    "Install for the processor (slower)": "Установить для процессора (медленнее)",
    "Interrupted again (MediaEngine was closed).": "Снова прервано (MediaEngine был закрыт).",
    "or a reel saved lately:": "или недавно сохранённый ролик:",
    "Voice-over add-on (optional)": "Модуль озвучки (по желанию)", "on the processor": "на процессоре",
    "needs to be installed again (Auto Edit → Voice-over)": "нужно установить заново (Автомонтаж → Озвучка)",
    "not installed - Auto Edit → Voice-over": "не установлен — Автомонтаж → Озвучка",
    "The voice add-on is being installed. Wait until it is ready.": "Модуль озвучки устанавливается. Подожди, пока он будет готов.",
    "The voice add-on is already installed.": "Модуль озвучки уже установлен.",
    "The start of the voice must be a number of seconds, for example 0.5.": "Начало голоса — это число секунд, например 0,5.",
    "Voice-over (Auto Edit → Voice-over, an add-on installed with a button): a text read by a voice, checked word by word, captions timed to the words, the voice and captions put onto a video.":
        "Озвучка (Автомонтаж → Озвучка, модуль ставится кнопкой): текст читает голос с проверкой каждого слова, "
        "субтитры точно по словам, голос и субтитры накладываются на видео.",
    "Voice-over: your picks from the voice test, the voices 4_4 and 4_2, instead of 3.1.":
        "Озвучка: твой выбор из пробы голосов — голоса 4_4 и 4_2 вместо 3.1.",
    "Voice-over: the voice 9_2 (your pick: cleaner; 9_3 lisped on s/sh/ch) - the only ready voice now; every piece of a voice-over is kept at the voice's own pitch.":
        "Озвучка: голос 9_2 (твой выбор: чище; 9_3 шепелявил на с/ш/ч) — теперь единственный готовый голос; каждый кусок озвучки "
        "держится на высоте этого голоса.",
    "Captions for your own videos: the speech becomes captions burned into a copy (Auto Edit → Voice-over).":
        "Субтитры для твоих видео: речь превращается в субтитры, вшитые в копию (Автомонтаж → Озвучка).",
    "A Windows window is open — it may be behind this window.": "Открыто окно Windows — оно может быть за этим окном.",
    "Nothing chosen. You can also paste the path.": "Ничего не выбрано. Можно вставить путь вручную.",
    "Choose the recording of the voice": "Выбери запись голоса", "Choose a video": "Выбери видео",
    "Install the voice add-on first.": "Сначала установи модуль озвучки.",
    "Type the text of the voice-over first.": "Сначала напиши текст озвучки.",
    "The text is too long for one voice-over (at most 5000 characters): split it into parts.":
        "Текст слишком длинный для одной озвучки (не больше 5000 знаков): раздели его на части.",
    "Choose a voice.": "Выбери голос.",
    "Describe the voice in a few words (for example: a calm man in his forties, deep voice).":
        "Опиши голос несколькими словами (например: a calm man in his forties, deep voice).",
    "Choose the recording of the voice (a WAV, MP3 or M4A of 5-30 seconds of one person speaking).":
        "Выбери запись голоса (WAV, MP3 или M4A: 5–30 секунд речи одного человека).",
    "The recording must be a sound file (WAV, MP3, M4A, FLAC, OGG).": "Запись должна быть звуковым файлом (WAV, MP3, M4A, FLAC, OGG).",
    "Choose a video (its full path) to make captions for.": "Выбери видео (полный путь), для которого нужны субтитры.",
    "This voice-over is not ready.": "Эта озвучка ещё не готова.", "Choose the video (its full path).": "Выбери видео (полный путь).",
    "No such voice-over.": "Такой озвучки нет.", "This one is being made now.": "Она сейчас делается.",
    "The voice add-on is already being installed.": "Модуль озвучки уже устанавливается.",
    "A voice-over is being made. Install when it is ready.": "Сейчас делается озвучка. Установи, когда она будет готова.",
    "The voice add-on is busy. Wait until it has finished.": "Модуль озвучки занят. Подожди, пока он закончит.",
    "The voice add-on needs MediaEngine's own Python 3.11.": "Модулю озвучки нужен собственный Python 3.11 из MediaEngine.",
    "The voice add-on is turned off on this PC (MEDIAENGINE_VOICE=off).": "Модуль озвучки выключен на этом компьютере (MEDIAENGINE_VOICE=off).",
    "Installation cancelled.": "Установка отменена.",
    "The add-on's Python parts could not be installed. Check the internet connection and try again (details for support: install.log in the add-on folder).":
        "Не удалось установить части модуля для Python. Проверь интернет и попробуй ещё раз (подробности для поддержки — install.log в папке модуля).",
    "Not enough free space on the disk of the data folder: the voice add-on needs about 26 GB free.":
        "Мало места на диске папки данных: модулю озвучки нужно около 26 ГБ свободного места.",
    "Not enough free space on the disk of the data folder: the voice add-on needs about 8 GB free.":
        "Мало места на диске папки данных: модулю озвучки нужно около 8 ГБ свободного места.",
    "Not enough free space left for the voice models.": "Не хватает места для голосовых моделей.",
    "No connection to the internet (or the site did not answer). Check the connection and try again.":
        "Нет связи с интернетом (или сайт не ответил). Проверь подключение и попробуй ещё раз.",
    "The voice worker took too long and was stopped.": "Озвучка шла слишком долго и была остановлена.",
    "The voice worker stopped without an answer (details: worker.log in the job folder).":
        "Модуль озвучки остановился без ответа (подробности — worker.log в папке задания).",
    "The recording of the voice could not be read.": "Не удалось прочитать запись голоса.",
    "The voice-over could not be finished (loudness).": "Не удалось довести звук озвучки.",
    "No speech was found in this video.": "В этом видео не найдено речи.",
    "This file has no picture: choose a video.": "В этом файле нет картинки: выбери видео.",
    "The length of this video could not be read.": "Не удалось узнать длину этого видео.",
    "FFmpeg is missing from this MediaEngine.": "В этом MediaEngine нет FFmpeg.",
    "The voice add-on is being installed (Auto Edit → Voice-over)": "Устанавливается модуль озвучки (Автомонтаж → Озвучка)",
    "A voice-over is being made (Auto Edit → Voice-over)": "Делается озвучка (Автомонтаж → Озвучка)",
    "A voice-over is being made (or the voice add-on installed). Switch when it is ready.":
        "Делается озвучка (или ставится модуль озвучки). Переключись, когда закончится.",
    # text on video and caption styles (textfx.py, voice_web.py)
    "Video with text and captions": "Видео с текстом и субтитрами",
    "Voice-over and text": "Озвучка и текст", "Voice-over and text · MediaEngine": "Озвучка и текст · MediaEngine",
    "Look of the captions": "Вид субтитров",
    "Bold capitals, the word being said in color (like Reels)": "Крупные жирные буквы, сказанное слово цветом (как в Reels)",
    "On a dark box, the word being said in color": "На тёмной плашке, сказанное слово цветом",
    "Classic: white with an outline, the words said turn to the color": "Классика: белые с обводкой, сказанные слова становятся цветными",
    "Calm: white with a soft shadow, no highlight (business)": "Спокойные: белые с мягкой тенью, без подсветки (деловой стиль)",
    "Color": "Цвет", "Yellow": "Жёлтый", "Green": "Зелёный", "Pink": "Розовый", "Blue": "Синий", "Orange": "Оранжевый",
    "White": "Белый", "Small": "Маленький", "Medium": "Средний", "Large": "Крупный",
    "On a colored stripe": "На цветной плашке", "Big white letters": "Крупные белые буквы", "On a dark box": "На тёмной плашке",
    "The text, e.g. 3 ways to fly cheaper": "Текст, например: 3 способа летать дешевле",
    "Remove this text": "Убрать этот текст",
    "Text on the video": "Текст на видео",
    "From and to: seconds of the finished video (2.5 or 0:12). “end” in “from” = the last 3 seconds; an empty “to” = 3 seconds later. An empty text is left out.":
        "«С» и «по» — секунды готового видео (2,5 или 0:12). «конец» в поле «с» — последние 3 секунды; пустое «по» — "
        "через 3 секунды. Пустой текст не добавляется.",
    "Add a text": "Добавить текст",
    "Preview": "Просмотр",
    "One picture of the finished video, with the captions and texts as they will be.":
        "Один кадр готового видео — с субтитрами и текстом, как они будут.",
    "At": "На", "Show": "Показать",
    "Making the picture…": "Делаю кадр…", "The picture could not be made.": "Не удалось сделать кадр.",
    "Title at the top (first 3 s)": "Заголовок вверху (первые 3 сек)",
    "optional": "не обязательно",
    "Text at the end (last 3 s)": "Текст в конце (последние 3 сек)",
    "optional, e.g. Follow for more": "не обязательно, например: Подпишись, будет больше",
    "Text on a video": "Текст на видео",
    "Titles and lines of text on your video, at the moments you choose. The video itself is only read; a copy with the text is made.":
        "Заголовки и строки текста на твоём видео в нужные моменты. Само видео только читается — делается копия с текстом.",
    "Edit text and captions": "Изменить текст и субтитры",
    "Edit text and captions · MediaEngine": "Изменить текст и субтитры · MediaEngine",
    "Fix a word right in its line (*word* = in the color); an emptied line is left out. −0.1 and +0.1 move a line by 0.1 s, ✂ splits it where the cursor is, ⤓ joins it with the next one, ＋ adds a line.":
        "Исправь слово прямо в строке (*слово* — цветом); пустая строка убирается. −0.1 и +0.1 сдвигают строку на 0,1 сек, ✂ разрезает её там, где "
        "курсор, ⤓ склеивает со следующей, ＋ добавляет строку.",
    "Only a finished video can be copied.": "Копию можно сделать только из готового видео.",
    "The small copy could not be made.": "Не удалось сделать маленькую копию.",
    "Optional: the exact text that is said - then the captions show it word for word, timed to the speech":
        "Не обязательно: точный текст того, что говорится, — тогда субтитры покажут его слово в слово, по времени речи",
    "(saved from a recording)": "(сохранён из записи)", "Delete this saved voice": "Удалить этот сохранённый голос",
    "Delete this saved voice?": "Удалить этот сохранённый голос?",
    "Keep this voice in the list, named": "Сохранить голос в списке с названием", "optional, e.g. Anna": "не обязательно, например: Анна",
    "Use only the voice of a person who agreed to it. A saved voice stays in this list.":
        "Используй голос только того человека, который на это согласен. Сохранённый голос останется в этом списке.",
    "Give the voice a name.": "Дай голосу название.", "No such voice.": "Такого голоса нет.",
    "There are already 20 saved voices: delete one first.": "Уже сохранено 20 голосов: сначала удали один.",
    "The recording of the voice could not be read (it needs at least a few seconds of speech).":
        "Не удалось прочитать запись голоса (нужно хотя бы несколько секунд речи).",
    "Save as a cover": "Сохранить как обложку", "This picture, full size, saved next to the reels": "Этот кадр в полном размере — рядом с роликами",
    "The cover could not be saved.": "Не удалось сохранить обложку.",
    "6. Music under it": "6. Музыка под видео", "(optional)": "(не обязательно)",
    "A song, e.g. D:\\Music\\calm.mp3": "Песня, например D:\\Музыка\\спокойная.mp3",
    "Loudness": "Громкость", "quiet": "тихо", "medium": "средне", "loud": "громко",
    "It gets quieter while the voice speaks.": "Пока говорит голос, она становится тише.",
    "Choose the music": "Выбери музыку",
    "Choose the music file (its full path).": "Выбери файл музыки (полный путь).",
    "The music must be a sound file (MP3, M4A, WAV, FLAC, OGG).": "Музыка должна быть звуковым файлом (MP3, M4A, WAV, FLAC, OGG).",
    "This music file has no sound that can be played.": "В этом файле музыки нет звука, который можно проиграть.",
    "Add a text, captions, a voice or music first.": "Сначала добавь текст, субтитры, голос или музыку.",
    "My looks:": "Мои виды:", "Delete the chosen look": "Удалить выбранный вид", "Name for this look": "Название этого вида",
    "Save the look": "Сохранить вид", "Give the look a name.": "Дай виду название.", "Saved.": "Сохранено.",
    "Pops in": "Выпрыгивает", "Slides up": "Выезжает снизу", "Fades in": "Проявляется", "Typed letter by letter": "Печатается по буквам",
    "Show where Reels, TikTok and Shorts put their own buttons and text (red)":
        "Показать, где Reels, TikTok и Shorts ставят свои кнопки и подписи (красным)",
    "0.1 s earlier": "На 0,1 сек раньше", "0.1 s later": "На 0,1 сек позже",
    "Split this line where the cursor is": "Разрезать строку там, где курсор", "Join with the next line": "Склеить со следующей строкой",
    "Add a line after this one": "Добавить строку после этой",
    "A new video is made; this one stays.": "Делается новое видео, это остаётся.",
    "Add a text (or captions) first.": "Сначала добавь текст (или субтитры).",
    "Only a finished video can be edited.": "Изменить можно только готовое видео.",
    "The voice-over of this video was deleted, so the video cannot be made again with its voice.":
        "Озвучка этого видео удалена, поэтому сделать его заново с голосом нельзя.",
    "The voice-over of this video was deleted.": "Озвучка этого видео удалена.",
    "When the text appears: write seconds, for example 2.5 or 0:12.": "Когда появляется текст: напиши секунды, например 2,5 или 0:12.",
    "When the text goes: write seconds, for example 2.5 or 0:12.": "Когда исчезает текст: напиши секунды, например 2,5 или 0:12.",
    "Text on a video (Auto Edit → Voice-over and text): titles and lines of text at the moments you choose, on a colored stripe, a dark box or in big letters - no add-on needed.":
        "Текст на видео (Автомонтаж → Озвучка и текст): заголовки и строки текста в нужные моменты — на цветной плашке, на тёмной плашке "
        "или крупными буквами; модуль озвучки не нужен.",
    "Captions in four looks (the word being said in color like Reels, on a dark box, classic, calm), with a color and a size; Edit text and captions fixes a word and shows a preview picture before the video is made.":
        "Субтитры в четырёх видах (сказанное слово цветом как в Reels, на тёмной плашке, классика, спокойные), с выбором цвета и "
        "размера; «Изменить текст и субтитры» — исправить слово и посмотреть кадр до того, как делать видео.",
    "Text, captions, voice-over": "Текст, субтитры, озвучка",
    "Finish a video: a saved reel → “Text, captions, voice-over” - the voice, captions, look and texts on one page, with a preview.":
        "Доделать видео: у сохранённого ролика → «Текст, субтитры, озвучка» — голос, субтитры, вид и текст на одной странице, "
        "с просмотром кадра.",
    "Finish a video": "Доделать видео", "Finish a video · MediaEngine": "Доделать видео · MediaEngine",
    "Finish a video - all on one page": "Доделать видео — всё на одной странице",
    "A voice, captions and text for one video, with their look - on one page.":
        "Голос, субтитры и текст для одного видео, вместе с их видом — на одной странице.",
    "1. The video": "1. Видео", "2. The voice": "2. Голос", "3. Captions": "3. Субтитры", "4. The look": "4. Вид",
    "5. Text on the video": "5. Текст на видео",
    "No voice (the video's own sound)": "Без голоса (свой звук видео)",
    "A voice-over made already": "Уже сделанная озвучка",
    "A new voice-over (made first, then the video)": "Новая озвучка (сначала она, потом видео)",
    "A new voice-over and captions of the speech need the voice add-on (Voice-over and text → Install the voice add-on).":
        "Для новой озвучки и субтитров речи нужен модуль озвучки (Озвучка и текст → Установить модуль озвучки).",
    "No captions": "Без субтитров", "The words of the voice": "Слова озвучки",
    "The speech in the video (heard when it is made)": "Речь в видео (распознаётся, когда делается видео)",
    "Choose the voice-over.": "Выбери озвучку.",
    "Captions of the voice need a voice: choose one, or captions of the video's speech.":
        "Для субтитров озвучки нужен голос: выбери его или субтитры речи в видео.",
    "Add a text, captions or a voice first.": "Сначала добавь текст, субтитры или голос.",
    "The video:": "Видео:",
    "It is already filled in below: put text on it, make captions of its speech, or put a voice-over on it (Made → a voice-over → Put it on a video).":
        "Оно уже подставлено ниже: можно добавить на него текст, сделать субтитры его речи или наложить озвучку "
        "(Сделано → озвучка → Наложить на видео).",
    "A text must be on the screen for at least 0.3 s (check its times).":
        "Текст должен быть на экране хотя бы 0,3 сек (проверь время).",
    "Pace": "Темп",
    "A livelier engine for the voices from a recording (the voice 9_2 - your pick 14_5)":
        "Более живой движок для голосов из записи (голос 9_2 — твой выбор 14_5)",
    "Qwen3-TTS says the voice 9_2, saved voices and voices from a recording more naturally. It is downloaded once: about 4.7 GB, into the same folder. Until then they are said by the engine they had.":
        "Qwen3-TTS говорит голосом 9_2, сохранёнными голосами и голосами из записи естественнее. Скачивается один раз: около 4,7 ГБ, "
        "в ту же папку. До этого они звучат на прежнем движке.",
    "Not enough free space: about 8 GB are needed while downloading.": "Мало свободного места: на время скачивания нужно около 8 ГБ.",
    "Download the new voice engine": "Скачать новый движок голоса",
    "Don't make it": "Не делать", "Stopped.": "Остановлено.",
    "One word at a time, big (like TikTok)": "По одному слову, крупно (как в TikTok)",
    "The word being said on a color block": "Сказанное слово на цветной плашке",
    "Captions in two more looks: one word at a time, big (like TikTok), and the word being said on a color block.":
        "Ещё два вида субтитров: по одному слову, крупно (как в TikTok), и сказанное слово на цветной плашке.",
    "Convert: “Save this picture” in Cut… - a photo of the moment in the player, at the video's full size, into the folder of converted videos.":
        "Конвертация: «Сохранить кадр» в «Обрезать…» — фото момента из плеера в полном размере видео, в папку готовых файлов.",
    "Convert: “Without sound” - the copy has no sound at all (wind, voices on site).":
        "Конвертация: «Без звука» — в копии совсем нет звука (ветер, разговоры на объекте).",
    "Convert: “Cut…” next to a video - only the part between start and end is converted (set with the player or typed as minutes:seconds).":
        "Конвертация: «Обрезать…» у видео — конвертируется только часть между началом и концом (задаётся плеером или вписывается как минуты:секунды).",
    "Convert: “Change…” - converted videos can go into a folder of yours (not a library folder); “Copy file” next to each one: Ctrl+V pastes it into a folder, an e-mail or a messenger.":
        "Конвертация: «Изменить…» — сжатые видео можно сохранять в свою папку (не в папку медиатеки); «Копировать файл» у каждого: Ctrl+V вставит его в папку, письмо или мессенджер.",
    "Convert: “Join into one video” - parts of one recording (a GoPro splits a long one into files of 4 GB: GX010044, GX020044 …) become one video, in the recording's order; several GoPro recordings - one video each.":
        "Конвертация: «Склеить в одно видео» — части одной записи (GoPro делит длинную запись на файлы по 4 ГБ: GX010044, GX020044 …) становятся одним видео, в порядке записи; несколько записей GoPro — по видео на каждую.",
    "Convert: “Choose videos on this PC…” converts any video on the computer without adding it to the library; “Stop” on a running conversion; the time left.":
        "Конвертация: «Выбрать видео на компьютере…» сжимает любое видео без добавления в медиатеку; «Остановить» во время конвертации; сколько осталось.",
    "Convert: big videos made smaller on an NVIDIA graphics card (much faster; if the card can't, the processor makes them as before); a Windows notification when a long conversion is ready.":
        "Конвертация: большие видео сжимаются на видеокарте NVIDIA (намного быстрее; если видеокарта не может — процессором, как раньше); уведомление Windows, когда долгая конвертация готова.",
    "Convert: “Show in folder” and “Open video” next to each converted file, and “Open the folder” at the top; the last job keeps its list of files until “Remove from the page” (the files stay in the folder).":
        "Конвертация: «Показать в папке» и «Открыть видео» у каждого готового файла и «Открыть папку» вверху; список последней конвертации остаётся, пока не нажать «Убрать со страницы» (файлы остаются в папке).",
    "Video with a voice-over": "Видео с озвучкой", "Video with captions": "Видео с субтитрами",
    "Video with captions and text": "Видео с субтитрами и текстом", "Video with music": "Видео с музыкой",
    "Video with text": "Видео с текстом", "Show the older ones too": "Показать и более старые",
    "Downloading the new voice engine": "Скачивается новый движок голоса",
    "Downloading the new voice engine's Python parts (about 0.2 GB)…": "Скачиваю части нового движка для Python (около 0,2 ГБ)…",
    "Downloading the new voice engine (Qwen3-TTS, about 4.5 GB)…": "Скачиваю новый движок голоса (Qwen3-TTS, около 4,5 ГБ)…",
    "The voice add-on's record could not be read. Try again.": "Не удалось прочитать запись о модуле озвучки. Попробуй ещё раз.",
    "Voice-over: the voice 9_2 is said by a new, livelier engine (Qwen3-TTS - your pick 14_5); an installed voice add-on downloads it with one button (about 4.7 GB).":
        "Озвучка: голос 9_2 теперь говорит на новом, более живом движке (Qwen3-TTS — твой выбор 14_5); установленный модуль "
        "озвучки докачивает его одной кнопкой (около 4,7 ГБ).",
    "Voices from a recording (9_2 too): Qwen3-TTS. A voice from a description: VoxCPM2.":
        "Голоса из записи (и 9_2): Qwen3-TTS. Голос по описанию: VoxCPM2.",
    "The new voice engine was installed but does not start:": "Новый движок голоса установлен, но не запускается:", "a bit slower": "чуть медленнее", "normal speed": "обычная скорость", "a bit faster": "чуть быстрее",
    "faster": "быстрее", "short pauses": "короткие паузы", "normal pauses": "обычные паузы", "long pauses": "длинные паузы",
    "between sentences; the voice keeps its own pitch": "между предложениями; высота голоса не меняется",
    "More videos, finished the same way": "Ещё видео — доделать так же",
    "The same voice, captions, look, texts and music on each; one new video per video (at most 30). The preview shows the first one.":
        "На каждое — тот же голос, субтитры, вид, текст и музыка; для каждого видео делается своё новое (не больше 30). "
        "Кадр для просмотра — из первого.",
    "One video per line, e.g. D:\\Exports\\reel2.mp4": "По одному видео в строке, например D:\\Экспорт\\ролик2.mp4",
    "or reels saved lately:": "или недавно сохранённые ролики:",
    "The exact text of the speech is for one video: clear it, or finish the videos one by one.":
        "Точный текст речи — только для одного видео: очисти его или доделай видео по одному.",
    "This video has no sound, so there is no speech to make captions of.":
        "В этом видео нет звука, поэтому нет речи для субтитров.",
    "At most 30 videos at once: split them into groups.": "Не больше 30 видео за раз: раздели их на группы.",
    "Finish a video: several videos at once - the same voice, captions, look, texts and music on each (one new video per video).":
        "Доделать видео: сразу несколько — на каждое тот же голос, субтитры, вид, текст и музыка (для каждого — своё новое видео).",
    "Voice-over: its pace - a bit slower or faster, shorter or longer pauses between sentences (the voice keeps its pitch, the captions follow); a voice from a recording can be kept in the voice list.":
        "Озвучка: темп — чуть медленнее или быстрее, короче или длиннее паузы между предложениями (высота голоса не меняется, "
        "субтитры следуют за голосом); голос из записи можно сохранить в списке голосов.",
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
    "' videos'": "' видео'",
    "' elapsed'": "' прошло'", "' · about '": "' · примерно '", "' min left'": "' мин осталось'",
    "' · less than a minute left'": "' · меньше минуты осталось'",
    "' · finding moments: '": "' · поиск моментов: '", "'less than a minute left'": "'меньше минуты осталось'",
    "'about '": "'примерно '", "', then cutting and joining'": "', потом нарезка и склейка'",
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
    "'write the time as seconds (12.5), minutes (1:05) or hours (1:05:03)'": "'напиши время в секундах (12.5), минутах (1:05) или часах (1:05:03)'",
    "'“to” must be at least 0.5 s after “from”'": "'«по» должно быть хотя бы на 0,5 с позже, чем «с»'",
    "'one moment can be at most 60 s long'": "'один момент — не длиннее 60 с'",
    "'Moment '": "'Момент '", "'Starting…'": "'Запуск…'", "'Installed.'": "'Установлено.'", "'Failed'": "'Не получилось'", "'the video is only '": "'видео длится всего '",
    "' s long - “to” cannot be later'": "' с — «по» не может быть позже'",
    "' · waiting until the reel is built'": "' · жду, пока соберётся ролик'",
    "' h left'": "' ч осталось'", "'For reels: '": "'Для роликов: '", "'Search: '": "'Поиск: '",
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
