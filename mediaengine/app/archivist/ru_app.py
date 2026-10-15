"""Russian texts for the whole app (pages outside Auto Edit; Auto Edit's own texts are in auto_edit_ru.py).

APP_PHRASES: the whole visible text of an element -> Russian.
APP_PATTERNS: texts with numbers/names in them (regex fullmatch -> replacement with \\1 groups).
APP_JS: quoted UI messages inside page scripts (only full quoted literals that are shown to the user).
"""
from __future__ import annotations

APP_PHRASES: dict[str, str] = {
    # ---- frame, home
    "Dashboard": "Главная", "Stop MediaEngine on this PC": "Остановить MediaEngine на этом компьютере",
    "Interface language: English": "Язык интерфейса: английский", "Язык интерфейса: русский": "Язык интерфейса: русский",
    "Local-first media workspace": "Локальная мастерская для видео",
    "Your footage, ready to work.": "Твои съёмки — готовы к работе.",
    "Browse Android, SD/USB and local folders in one place. Library stays clean: only media you explicitly add becomes part of the working collection.":
        "Android, SD/USB и папки на компьютере — в одном месте. Библиотека остаётся чистой: в неё попадает только то, что ты сам добавил.",
    "Start here": "С чего начать", "Import new media": "Импорт нового", "Open Library": "Открыть библиотеку",
    "Check this PC": "Проверка компьютера",
    "On sources": "На источниках", "Waiting to import": "Ждут импорта", "In Library": "В библиотеке", "Library videos": "Видео в библиотеке",
    "Privacy review": "Проверка приватности", "Rights review": "Проверка прав",
    "Android source": "Android-источник", "Jobs": "Задачи", "How it works": "Как это работает",
    "Browse every source in": "Просмотри любой источник в разделе Медиа →", "Import": "Импорт", "→ select what you want →": "→ выбери нужное →",
    "Add to Library": "Добавить в библиотеку", "or": "или", "Add + Analyze": "Добавить + анализ",
    ". Local-folder files stay in place; Android/SD files copy to Staging. Private and Rejected media never appear in Library.":
        ". Файлы из папок остаются на месте; файлы с Android/SD копируются в промежуточную папку (Staging). Личное (Private) и отклонённое (Rejected) никогда не попадают в библиотеку.",
    "This is a separate MediaEngine install.": "Это отдельная установка MediaEngine.",
    "The Library is empty.": "Библиотека пуста.",
    "Your projects are not shown.": "Твои проекты не показаны.",
    "More": "Ещё",
    "Making a reel": "Собирается ролик", "Open the reel": "Открыть ролик",
    "Optional, not set up: copy the phone videos to this PC and choose that folder.": "По желанию, не настроено: скопируй видео с телефона на компьютер и выбери эту папку.",
    "Make a reel": "Сделать ролик", "Select videos first": "Сначала выбери видео",
    "No selected video is on this PC now (photos are not used in reels).": "Ни одного выбранного видео сейчас нет на этом компьютере (фото в роликах не используются).",
    "Reel projects": "Проекты роликов",
    "Publication history and detailed novelty signals stay in the local MediaEngine database. Nothing is sent anywhere.": "История публикаций и подробные сигналы новизны хранятся в локальной базе MediaEngine. Ничего никуда не отправляется.",
    "Open in player": "Открыть в плеере", "Make a reel from this video": "Сделать ролик из этого видео",
    "The file is not available on this PC now (disk not connected?).": "Файла сейчас нет на этом компьютере (диск не подключён?).",
    "Not available": "Недоступно",
    "The data folder was not found:": "Папка с данными не найдена:",
    "Connect that disk (or put the folder back) and restart MediaEngine. Until then an empty folder is used:": "Подключи этот диск (или верни папку на место) и перезапусти MediaEngine. Пока используется пустая папка:",
    "The database may be damaged.": "База данных, возможно, повреждена.",
    "Copies of it are kept in the backups folder:": "Её копии лежат в папке резервных копий:",
    "Add a folder on Import, or make a reel straight from a folder of videos with Auto Edit.":
        "Добавь папку в «Импорте» или сразу собери ролик из папки с видео в «Автомонтаже».",
    "analysis": "анализ", "cutting": "нарезка", "joining": "склейка", "reel": "ролик", "Built in": "Собрано за", "min": "мин",
    "on": "включены", "files changed or incomplete - not used": "файлы изменены или неполные — не используются",
    "missing - HDR video will look grey": "нет — HDR-видео будет серым",
    "Memory (RAM)": "Память (ОЗУ)", "MediaEngine version": "Версия MediaEngine",
    "Free space on the data drive": "Свободно на диске данных", "Program folder": "Папка программы",
    "ADB not installed": "ADB не установлен", "not connected": "не подключён", "Working…": "Работаю…",
    # ---- activity, jobs
    "Activity": "Активность", "Operations": "Работа", "Jobs & errors": "Задачи и ошибки",
    "Inspect failed jobs, retry safely, and review local diagnostic/support boundaries.":
        "Смотри неудачные задачи, безопасно повторяй их и проверяй, что остаётся на компьютере.",
    "Jobs, failures and recovery history live here. Existing job details remain unchanged.":
        "Здесь история задач, ошибок и восстановления. Подробности задач не меняются.",
    "Open the existing durable job history.": "Открыть историю задач.", "Publishing activity": "Публикации",
    "Recovery & support": "Восстановление и поддержка",
    "Will appear here only after Social Lab publishing is implemented.": "Появится здесь, когда в Social Lab заработают публикации.",
    "Live queue. Running jobs refresh automatically; completed jobs keep their actual start, finish and elapsed time.":
        "Очередь в реальном времени. Идущие задачи обновляются сами; у завершённых сохраняются время начала, конца и длительность.",
    # ---- auto edit leftovers (whole texts)
    "AI model (FAST_LOCAL)": "ИИ-модель (FAST_LOCAL)",
    "AI model not available — build with Technical only (sharpness, motion, exposure)":
        "ИИ-модель недоступна — сборка в режиме «Только техника» (резкость, движение, свет)",
    "Export MP4": "Экспорт MP4", "not found": "не найдено",
    # ---- help
    "Help & recovery": "Помощь и восстановление", "Help & Recovery": "Помощь и восстановление",
    "Local troubleshooting first. Nothing here silently uploads media, tokens, or diagnostics.":
        "Сначала разбираемся на месте. Отсюда ничего не отправляется тайком — ни видео, ни ключи, ни диагностика.",
    "Local-first reminder:": "Напоминание: всё работает локально.",
    "No external account or billing is required for local use. Optional provider or cloud workflows remain user-initiated.":
        "Для работы на компьютере не нужны ни аккаунты, ни оплата. Облако и внешние сервисы — только если ты сам их включишь.",
    "Open Activity": "Открыть активность",
    "Open Activity → Jobs & errors to inspect durable job history. Failed jobs can be retried from their job detail page; running jobs can be cancelled safely.":
        "Активность → Задачи и ошибки: там история задач. Неудачную задачу можно повторить на её странице; идущую — безопасно отменить.",
    "Open Jobs & errors": "Открыть задачи и ошибки", "Recovery safety": "Безопасное восстановление",
    "About update safety": "О безопасных обновлениях",
    "Update health checks can restore the previous build when a new release fails to start. Recovery does not weaken privacy settings and never deletes source originals.":
        "Если новая версия не запускается, проверка при обновлении возвращает прежнюю. Восстановление не ослабляет приватность и никогда не удаляет оригиналы.",
    "Support bundle ready": "Пакет для поддержки готов", "Support bundle created locally": "Пакет для поддержки создан на компьютере",
    "Location: MediaEngine local data/support folder. Nothing was uploaded.": "Где: папка data/support в данных программы. Ничего не отправлено.",
    "Back to Help": "Назад в помощь",
    "Support data": "Данные для поддержки", "Beta support": "Поддержка (бета)",
    "Create a local support bundle": "Собрать пакет для поддержки на этом компьютере", "Create support bundle": "Собрать пакет для поддержки",
    "Creates a bounded, sanitized ZIP on this PC only. It is never uploaded automatically and excludes raw media, credentials, database contents and full personal paths.":
        "Создаёт небольшой очищенный ZIP только на этом компьютере. Он никуда не отправляется сам и не содержит видео, паролей, содержимого базы и полных личных путей.",
    "Support export/upload is explicit opt-in only; this beta does not auto-upload support data. Raw media and tokens are excluded by default.":
        "Отправка данных для поддержки — только по твоему решению; эта версия ничего не отправляет сама. Видео и ключи не включаются.",
    "Diagnostics": "Диагностика",
    "Diagnostics stay local by default. They are for local troubleshooting and release acceptance unless you explicitly choose to share diagnostic information.":
        "Диагностика остаётся на компьютере. Она нужна для разбора проблем и проверки версий, пока ты сам не решишь ею поделиться.",
    "Review Connections": "Проверить подключения", "Open bundled Beta Guide": "Открыть руководство (бета)",
    "MediaEngine Beta Guide": "Руководство MediaEngine (бета)", "Beta guide": "Руководство (бета)",
    "Bundled local-first beta guidance from this installed build.": "Руководство, встроенное в эту версию.",
    # ---- welcome
    "A reel from your own videos:": "Ролик из своих видео:",
    "open Auto Edit, choose a folder (or single videos), pick length, format and sound.": "открой «Автомонтаж», выбери папку (или отдельные видео), длину, формат и звук.",
    "First run": "Первый запуск", "Start local. Add only what you need.": "Начни на компьютере. Добавляй только нужное.",
    "MediaEngine is local-first. Your media stays on this PC unless you explicitly connect a provider or enable an optional cloud workflow.":
        "Всё работает на компьютере. Твои видео остаются здесь, пока ты сам не подключишь сервис или облако.",
    "1 · Add a media source": "1 · Добавь источник видео", "2 · Review optional connections": "2 · Посмотри необязательные подключения",
    "3 · Help & recovery": "3 · Помощь и восстановление", "Manage sources": "Источники", "Review privacy": "Приватность",
    "Required vs optional": "Обязательное и необязательное", "Required": "Обязательно", "Optional": "Необязательно", "Included": "Бесплатно, входит в программу",
    "Core & Local AI": "Основное и локальный ИИ", "Local ingest, search, analysis, conversion and composition.":
        "Загрузка, поиск, анализ, конвертация и монтаж — на компьютере.",
    "Media Sources": "Источники видео", "Folders, removable media and supported phone ingest.": "Папки, съёмные носители и телефоны.",
    "Social Accounts": "Соцсети", "Future publishing, analytics and experiment feedback.": "Будущие публикации, аналитика и эксперименты.",
    "Optional Online AI": "Онлайн-ИИ (необязательно)", "Future opt-in tasks that cannot or should not run locally.":
        "Будущие задачи по желанию, которые нельзя или не стоит делать на компьютере.",
    "Optional backup, mirror and cross-device recovery.": "Резервная копия, зеркало и восстановление на другом устройстве — по желанию.",
    "Media-source phones and future Social Device Lab handoff/QA.": "Телефоны как источник видео и будущая проверка публикаций.",
    "Cost": "Стоимость", "Data": "Данные", "Status": "Состояние", "No MediaEngine fee": "Программа бесплатна",
    "Platform/provider rules apply": "Действуют правила платформы", "Provider charges may apply": "Сервис может брать плату",
    "Provider/model charges may apply": "Сервис или модель могут брать плату", "Manage locally": "Управляется на компьютере",
    "Media stays on this device by default.": "Видео остаются на этом устройстве.",
    "Discovery is local. Source originals are never auto-deleted.": "Поиск — на компьютере. Оригиналы никогда не удаляются сами.",
    "Device registration is per installation; no personal device is hard-coded.": "Устройства регистрируются в каждой установке; ничьё личное устройство не прописано.",
    "Disabled by default. Only explicitly selected upload modes may leave the device.": "Выключено. Наружу уходит только то, что ты сам выбрал для загрузки.",
    "No social account credentials are configured in this release.": "Аккаунты соцсетей в этой версии не настроены.",
    "No user media is sent to online AI by this foundation release.": "Эта версия не отправляет видео в онлайн-ИИ.",
    "No external account or billing is required for local use.": "Для работы на компьютере не нужны аккаунты и оплата.",
    "Not connected": "Не подключено", "Open Devices": "Открыть устройства", "Open Media": "Открыть медиа", "Open Social Lab": "Открыть Social Lab",
    "Review Cloud": "Облако",
    "Cloud, social-provider and online-AI features are optional. They stay off or unconfigured until you explicitly enable or connect them.":
        "Облако, соцсети и онлайн-ИИ — по желанию. Они выключены, пока ты сам их не включишь.",
    "Analytics boundary": "Границы аналитики",
    "Provider analytics keep their source provenance and remain descriptive. MediaEngine does not automatically choose a cross-provider winner or create an opaque ranking.":
        "Аналитика сервисов показывается как есть, с указанием источника. Программа сама не выбирает «победителя» и не строит скрытых рейтингов.",
    "Nothing leaves this PC by default. If you explicitly connect a provider or start an optional upload, authentication data, selected uploads, and provider analytics can be sent to that service.":
        "По умолчанию ничего не уходит с компьютера. Если ты подключишь сервис или начнёшь загрузку, этому сервису уйдут данные входа, выбранные файлы и его аналитика.",
    "Provider credentials belong in Windows Credential Manager, not MediaEngine SQLite or Supabase. Cloud Vault is off by default and enabling cloud never deletes local or source originals.":
        "Пароли сервисов хранятся в диспетчере учётных данных Windows, а не в базе программы. Облако выключено; его включение никогда не удаляет файлы на компьютере и оригиналы.",
    # ---- about
    "About": "О программе", "Why we built it": "Зачем это сделано", "Who is building it": "Кто делает",
    "Your footage may already be spread across phones, cameras, cards and old folders while the useful moments stay buried inside thousands of files. MediaEngine is a private workspace designed to turn that mess into a usable creative library.":
        "Съёмки разбросаны по телефонам, камерам, картам и старым папкам, а хорошие моменты теряются в тысячах файлов. Эта программа — личная мастерская, которая превращает этот беспорядок в удобную библиотеку.",
    "local-first": "всё на компьютере", "privacy-first": "приватность прежде всего", "AI-assisted": "с помощью ИИ", "built for video": "для видео",
    "Built local-first": "Сделано для работы на компьютере",
    "MediaEngine is being shaped around real mixed-device media workflows: explicit import, source safety, private local analysis, nondestructive editing and clear control over every optional external connection.":
        "Программа строится вокруг реальной работы с разными устройствами: явный импорт, сохранность оригиналов, приватный анализ на компьютере, монтаж без порчи файлов и полный контроль над внешними подключениями.",
    "The product identity is installation-neutral: no personal paths, devices, accounts or credentials are built into defaults.":
        "В программу не встроены ничьи личные пути, устройства, аккаунты или пароли.",
    "The idea": "Идея", "One place between the camera and the final story.": "Одно место между камерой и готовой историей.",
    "We do not want another photo viewer. We want MediaEngine to remember what we chose, protect what must stay private, understand what is inside long videos, and surface the clips that are actually worth using.":
        "Нам не нужен ещё один просмотрщик. Программа должна помнить наш выбор, защищать личное, понимать, что внутри длинных видео, и находить моменты, которые действительно стоит использовать.",
    "Keep the originals safe": "Оригиналы в сохранности",
    "Phone, SD and camera originals are never automatically deleted or rewritten.": "Оригиналы с телефона, SD и камеры никогда не удаляются и не перезаписываются сами.",
    "Private means private": "Личное — значит личное",
    "Private Forever stays out of the normal Library and future creative workflows.": "«Личное навсегда» не попадает ни в библиотеку, ни в монтаж.",
    "AI suggests, we decide": "ИИ предлагает, решаем мы",
    "Quality, privacy and rights checks help us review; they do not silently make destructive decisions.":
        "Проверки качества, приватности и прав помогают, но ничего не удаляют молча.",
    "Where we are": "Где мы сейчас", "Import → Library": "Импорт → Библиотека",
    "Browse Android, SD/USB and local folders in Import; only selected media becomes the working collection.":
        "В «Импорте» видно Android, SD/USB и папки; в работу идёт только выбранное.",
    "Understand video": "Понимание видео",
    "Storyboards and hover previews are the start; semantic tags and scene-level understanding come next.":
        "Раскадровки и превью при наведении — начало; дальше смысловые теги и понимание сцен.",
    "Virtual clips": "Виртуальные клипы", "Mark useful moments without cutting or duplicating the original file.":
        "Отмечай удачные моменты, не разрезая и не копируя оригинал.",
    "Content Composer": "Монтаж", "The long-term goal: ask for a story or Reel and let the system find the right safe, useful moments from your own archive.":
        "Цель: попросить историю или ролик — и программа сама найдёт подходящие безопасные моменты в твоём архиве.",
    "Our rules": "Наши правила", "Privacy, quality and publishing rights stay separate.": "Приватность, качество и права на публикацию — отдельно.",
    "A technically beautiful clip can still be private or need a rights review.": "Технически красивый клип может быть личным или требовать проверки прав.",
    "No mystery copies.": "Никаких тайных копий.", "Import is explicit. Library means the local working set.": "Импорт — только явный. Библиотека — это рабочий набор на компьютере.",
    "No automatic source cleanup.": "Источники сами не чистятся.",
    "Disconnect only after MediaEngine explicitly says the source is safe to disconnect.": "Отключай носитель только после того, как программа скажет, что можно.",
    "No fake certainty.": "Никакой ложной уверенности.",
    "Rights Guard flags risk and context; it does not pretend every venue question has a simple legal yes/no answer.":
        "Проверка прав отмечает риски, но не делает вид, что на любой вопрос есть простой юридический ответ «да/нет».",
    "This installation": "Эта установка", "Version": "Версия", "Data folder": "Папка данных", "Program folder": "Папка программы",
    "Staging": "Промежуточная папка (Staging)", "Update safety": "Безопасные обновления", "Updates should fail safe.": "Неудачное обновление не должно ломать программу.",
    "The permanent launcher now health-checks a newly installed release and can restore the previous backup if the new build does not come up correctly.":
        "Запуск проверяет новую версию и возвращает предыдущую, если новая не поднялась.",
    # ---- settings
    "Settings": "Настройки", "Configuration": "Настройки", "Storage": "Хранение", "Behavior": "Поведение",
    "Storage, privacy and local analysis behavior. External capabilities are managed separately in Setup & Connections.":
        "Хранение, приватность и анализ на компьютере. Внешние сервисы — отдельно, в «Подключениях».",
    "Setup & Connections": "Подключения", "Interface language": "Язык интерфейса",
    "(projects, database, exports — kept outside the program folder, shared by every release)":
        "(проекты, база, экспорт — вне папки программы, общие для всех версий)",
    "Archive folder": "Папка архива", "Private": "Личное (Private)", "Rejected quarantine": "Карантин отклонённых (Rejected)",
    "Free-space reserve GB": "Запас свободного места, ГБ", "Privacy screening": "Проверка приватности",
    "Technical quality triage": "Отбор по техническому качеству", "Save settings": "Сохранить настройки",
    "about": "примерно", "min left": "мин осталось", "less than a minute left": "меньше минуты осталось",
    "Windows notification when a reel that took more than a minute is ready":
        "Уведомление Windows, когда готов ролик, который собирался дольше минуты",
    "Existing local sources": "Источники на компьютере", "Label": "Название", "Add source": "Добавить источник", "Remove": "Удалить",
    "Rights Guard": "Проверка прав",
    "Privacy, technical quality and publishing-rights risk stay separate. Rights flags are conservative workflow hints, not legal determinations. Manual rights decisions are preserved across later analysis.":
        "Приватность, техническое качество и риск по правам — отдельно. Отметки о правах — осторожные подсказки, а не юридическое решение. Ручные решения сохраняются при новом анализе.",
    # ---- connections
    "Provider connections are local-first. This page never asks ordinary users for API secrets.":
        "Подключения сервисов — под твоим контролем. Эта страница не просит ключей API.",
    "What can leave this PC": "Что может уйти с компьютера",
    "Connecting a provider can send authentication data, selected uploads, and provider analytics to that service. Provider credentials stay in Windows Credential Manager, not MediaEngine SQLite or Supabase. Nothing is connected automatically.":
        "При подключении сервиса ему могут уйти данные входа, выбранные файлы и его аналитика. Пароли хранятся в диспетчере учётных данных Windows, не в базе программы. Само ничего не подключается.",
    "Manual fallback": "Вручную", "Manual handoff": "Ручная передача", "Analytics CSV": "Аналитика из CSV",
    "Manual handoff and Analytics CSV remain available while official provider OAuth is blocked or not registered.":
        "Ручная передача и CSV-аналитика доступны, пока официальный вход сервиса не настроен.",
    "Connect": "Подключить", "Blocked": "Заблокировано", "Client ID: Missing": "Client ID: нет", "Official OAuth: Not enabled": "Официальный вход: выключен",
    "Preflight: Blocked": "Проверка: заблокировано", "Credentials: blocked_until_os_secret_store": "Пароли: нужен защищённый склад Windows",
    "os_secret_store_unavailable": "защищённый склад паролей недоступен", "not_configured": "не настроено",
    "backend_token_broker_not_configured": "сервер ключей не настроен", "meta_secret_flow_not_enabled": "вход Meta не включён",
    "youtube_client_id_missing": "нет Client ID для YouTube", "verifier_missing": "нет проверки входа",
    "Preflight: Ready": "Проверка: готово", "Official OAuth: Enabled": "Официальный вход: включён", "Client ID: Configured": "Client ID: настроен",
    "ffmpeg_unavailable": "FFmpeg недоступен", "privacy_detector_unavailable": "проверка приватности недоступна",
    "preview_unavailable": "превью недоступно", "storyboard_unavailable": "раскадровка недоступна", "source_missing": "исходника нет",
    "composition_sources_missing": "исходников монтажа нет", "optional_unavailable": "необязательное недоступно",
    # ---- media hub, library, import, convert, search, best
    "Media": "Медиа", "Media workspace": "Медиа",
    "Ingest, understand, find, convert and compose from the local working library. Existing media routes remain unchanged under this section.":
        "Загрузка, анализ, поиск, конвертация и монтаж из рабочей библиотеки на компьютере.",
    "Browse folders, Android and removable sources.": "Папки, Android и съёмные носители.",
    "The media you explicitly selected for work.": "То, что ты сам выбрал для работы.",
    "Review Media Brain virtual clips.": "Виртуальные клипы, найденные анализом.",
    "Local semantic signals and Find Similar.": "Поиск по описанию и похожим кадрам — на компьютере.",
    "Create local derived copies without altering originals.": "Уменьшенные копии без изменения оригиналов.",
    "Build nondestructive multi-clip compositions.": "Монтаж из нескольких клипов без изменения оригиналов.",
    "Folder of videos → finished reel from the best moments.": "Папка с видео → готовый ролик из лучших моментов.",
    "Composer": "Монтаж", "Search": "Поиск", "Library": "Библиотека", "Convert": "Конвертация", "Best Moments": "Лучшие моменты",
    "Working collection": "Рабочая коллекция", "Search Library": "Поиск в библиотеке", "Import more": "Импортировать ещё",
    "Analyze local": "Анализировать", "Apply rights tag": "Отметить права", "Private forever": "Личное навсегда",
    "Reject → quarantine": "Отклонить → карантин", "Remove from Library": "Убрать из библиотеки", "Jobs / errors": "Задачи / ошибки",
    "Hover over a video when its storyboard is ready to skim the clip without opening it.":
        "Наведи мышь на видео с готовой раскадровкой, чтобы пролистать его, не открывая.",
    "Import sources": "Источники импорта", "Source browser": "Обзор источников",
    "One place for Android, SD/USB and folders already on this computer. Choose what becomes part of Library.":
        "Android, SD/USB и папки на компьютере — в одном месте. Выбери, что войдёт в библиотеку.",
    "Local folders stay where they are. Android and SD/USB files are copied to Staging only after you select them.":
        "Папки на компьютере остаются на месте. Файлы с Android и SD/USB копируются в Staging, только когда ты их выберешь.",
    "Local-folder files stay in place. Android/SD files are copied to Staging. Source originals are never deleted.":
        "Файлы из папок остаются на месте. Файлы с Android/SD копируются в Staging. Оригиналы никогда не удаляются.",
    "Label (optional)": "Название (необязательно)", "Add folder + Discover": "Добавить папку и найти видео",
    "Discover all sources": "Найти во всех источниках", "No local folders added yet.": "Папки ещё не добавлены.",
    "Nothing here with the current filters.": "С такими фильтрами ничего нет.", "Search source media": "Поиск по источникам",
    "Apply": "Применить", "Go": "Перейти", "First": "Первая", "Last": "Последняя", "Next": "Следующая", "Previous": "Предыдущая",
    "Page": "Страница", "Select page": "Выбрать страницу", "Previews …": "Превью …", "local-source": "папка на компьютере",
    "Local video utility": "Утилита для видео",
    "Make smaller shareable copies without touching originals. Converted files go into the":
        "Делает уменьшенные копии для отправки, не трогая оригиналы. Готовые файлы попадают в папку",
    "folder of this installation; source folders and cards are never written to.":
        "этой установки; в папки-источники и на карты ничего не записывается.",
    "Search local videos": "Поиск видео", "Filter": "Фильтр", "Clear": "Сбросить", "Accessible on this catalog page": "Доступны на этой странице",
    "Add / discover a folder": "Добавить / найти папку",
    "No accessible videos on this catalog page. Reconnect/restore the source, choose another page, or clear the filter.":
        "На этой странице нет доступных видео. Подключи источник, выбери другую страницу или сбрось фильтр.",
    "Preset": "Пресет", "Choose a preset. For messengers / sharing, Share 1080p is the balanced option.":
        "Выбери пресет. Для мессенджеров лучше всего подходит Share 1080p.",
    "Share 1080p": "Share 1080p", "High Quality 1080p": "Высокое качество 1080p", "Small 720p": "Маленький 720p",
    "Original Resolution": "Исходное разрешение", "balanced for messengers / sharing": "баланс для мессенджеров",
    "best-looking smaller 1080p copy": "лучшая по виду уменьшенная копия 1080p", "smallest practical share copy": "самая маленькая копия для отправки",
    "keep 4K / source resolution · lower bitrate": "оставить 4K / исходное разрешение · меньше битрейт",
    "Fit under (optional)": "Уложиться в размер (необязательно)", "Target size uses two-pass encoding and may take longer.":
        "Заданный размер — кодирование в два прохода, дольше.",
    "Estimate is shown before conversion and may vary with image complexity.": "Оценка размера показана заранее и может отличаться.",
    "Select videos to see estimated output size.": "Выбери видео, чтобы увидеть примерный размер.", "Convert selected": "Конвертировать выбранные",
    "Converted": "Готово",
    "Search your footage": "Поиск по съёмкам", "Local Search / M7": "Поиск на компьютере",
    "Describe useful properties of the media. Search runs locally and uses MediaEngine's existing Media Brain and catalog signals.":
        "Опиши, что ищешь. Поиск идёт на компьютере по данным анализа и каталога.",
    "e.g. best vertical high-motion videos": "например: лучшие вертикальные видео с движением",
    "Best vertical": "Лучшие вертикальные", "Dark / night": "Тёмные / ночь", "Drone": "Дрон", "High motion": "Много движения", "Long Android": "Длинные с Android",
    "Try one of the examples above. Nothing leaves this computer.": "Попробуй пример выше. Ничего не уходит с компьютера.",
    "Understands: orientation, duration, motion, brightness, quality, source, audio, privacy, rights, Media Brain score, filename/source text. Exact people/objects/scenes that are not already in local text are not vision-indexed yet; this page is the stable foundation for a future optional local visual-embedding layer.":
        "Понимает: ориентацию, длительность, движение, яркость, качество, источник, звук, приватность, права, оценку анализа, имя файла. Конкретных людей, предметы и сцены пока не распознаёт.",
    "Media Brain": "Анализ видео", "Videos": "Видео",
    "Virtual clips ranked from your existing footage. Nothing here creates a new video file.":
        "Виртуальные клипы из твоих съёмок, по оценке. Новые файлы здесь не создаются.",
    "No Media Brain clips yet. Select local videos in Library and run Media Brain.":
        "Клипов пока нет. Выбери видео в библиотеке и запусти анализ.",
    "Open clip": "Открыть клип",
    # ---- clip, composer, item, similar
    "Virtual clip": "Виртуальный клип", "← Best Moments": "← Лучшие моменты", "Why this clip": "Почему этот клип",
    "Only this virtual interval is played. The source video is not cut or rewritten.": "Играет только этот отрезок. Исходное видео не режется и не меняется.",
    "Play": "Играть", "Replay clip": "Повторить", "Full video": "Всё видео", "Original": "Оригинал",
    "Smart Crop v1": "Умное кадрирование v1", "Open Smart Crop v2 review": "Открыть умное кадрирование v2",
    "The selected crop is static per virtual clip. Smart Crop v2 remains behind its feature flag until Windows acceptance.":
        "Кадрирование одно на весь клип. Версия 2 пока выключена.",
    "Preset: general": "Пресет: общий", "Rebuild as Car / dashboard": "Пересобрать как «машина / видеорегистратор»",
    "M8 / Local Render": "Сборка на компьютере", "Export clip": "Экспорт клипа",
    "Create a new MP4 from this virtual clip. Original footage stays untouched. Smart Crop export uses the approved static crop plan for this first render layer.":
        "Создаёт новый MP4 из этого клипа. Оригинал не меняется. Используется утверждённое кадрирование.",
    "Content Composer": "Монтаж", "M8 / Content Composer": "Монтаж",
    "Select existing Virtual Clips, choose one target aspect and build a local composition. Renders run locally in the background with normalized stereo audio; silent clips receive silence so every segment concatenates reliably. Originals stay untouched.":
        "Выбери клипы и формат кадра — получится монтаж. Сборка идёт на компьютере в фоне, звук выравнивается; оригиналы не меняются.",
    "Composition title": "Название", "Create composition": "Создать монтаж", "Recent compositions": "Последние монтажи",
    "Up to 20 clips / 180 seconds": "До 20 клипов / 180 секунд", "draft": "черновик", "Composition": "Монтаж",
    "Render composition": "Собрать монтаж", "Render MP4": "Собрать MP4",
    "Local MP4 rendered in the background. Every segment is normalized to the target aspect and stereo AAC; silent clips receive a silent track. Existing Smart Crop plans are used when available.":
        "MP4 собирается на компьютере в фоне. Каждый кусок приводится к нужному кадру и звуку; используется готовое кадрирование.",
    "Virtual clips + Smart Crop": "Виртуальные клипы и кадрирование", "Find similar": "Найти похожие", "Find Similar": "Похожие",
    "Generating locally… They will appear here automatically; no reload and no Explorer needed.": "Создаются на компьютере… Появятся здесь сами.",
    "Rebuild": "Пересобрать", "Type": "Тип", "Duration": "Длительность", "Audio present": "Есть звук", "Error": "Ошибка",
    "Privacy": "Приватность", "Privacy reason": "Причина (приватность)", "Quality": "Качество", "Quality reason": "Причина (качество)",
    "Rights": "Права", "Rights reason": "Причина (права)", "Rights / location risk": "Права / риск места съёмки", "Rights place": "Место",
    "Rights source": "Источник", "Rights notes": "Заметки о правах", "Place / venue": "Место / площадка", "Policy/source URL": "Ссылка на правила",
    "Notes": "Заметки", "Save rights status": "Сохранить права", "Rejected": "Отклонённые (Rejected)", "Remove source": "Убрать источник", "Find by theme (AI+)": "Найти по теме (ИИ+)", "Find": "Найти",
    "Prepare the search": "Подготовить поиск", "Find by theme": "Поиск по теме", "best moment": "лучший момент",
    "Prepare AI+ for the whole Library": "Подготовить ИИ+ для всей Библиотеки", "Stop preparing": "Остановить подготовку",
    "AI+ is prepared for the whole Library.": "ИИ+ подготовлен для всей Библиотеки.",
    "The AI+ preparation ended unexpectedly. Press the button again: it continues where it stopped.":
        "Подготовка ИИ+ неожиданно прервалась. Нажми кнопку ещё раз — она продолжится с того же места.",
    "The computer looks at every video once: it can run overnight, waits while a reel is being built and continues where it stopped. After that every search is instant and AI+ reels are built much faster.":
        "Компьютер один раз просматривает каждое видео: можно оставить на ночь, на время сборки ролика подготовка ждёт и потом продолжается с того же места. После этого любой поиск мгновенный, а ролики с ИИ+ собираются намного быстрее.",
    "The AI+ model looks at the preview frames of each video once (about 10-20 s per video on a normal PC); after that every search is instant.":
        "Модель ИИ+ один раз смотрит кадры превью каждого видео (примерно 10–20 с на видео на обычном компьютере); после этого любой поиск мгновенный.",
    "No video matches this theme.": "Ни одно видео не подходит под эту тему.", "Library · AI+": "Библиотека · ИИ+", "Make a reel about this theme": "Собрать ролик на эту тему", "Choose a theme.": "Выбери тему.",
    "Sea and beach": "Море и пляж", "Mountains": "Горы", "Children": "Дети", "Family and friends": "Семья и друзья",
    "Celebration": "Праздник", "Animals": "Животные", "Sunset": "Закат", "Nature": "Природа", "Winter and snow": "Зима и снег",
    "City": "Город", "Food": "Еда", "Sport": "Спорт", "Road trip": "Дорога и поездки", "Aerial view (drone)": "Вид сверху (дрон)",
    "Open one to start at its best moment.": "Открой видео — оно начнётся с лучшего момента.",
    "Stopped.": "Остановлено.", "The AI+ model could not be started (not enough memory?). Close other programs and try again.":
        "Модель ИИ+ не запустилась (не хватает памяти?). Закрой другие программы и попробуй ещё раз.", "The AI+ model is not on this computer yet. Download it once on 'Check this PC'.":
        "Модели ИИ+ на этом компьютере пока нет. Скачай её один раз на странице «Проверка компьютера».", "Clip not found": "Клип не найден (видео проанализировано заново или убрано)",
    "Not found": "Не найдено",
    "privacy_clear": "личного не найдено", "privacy_candidate": "возможно личное — проверь", "privacy_disabled": "проверка приватности выключена", "privacy_not_run": "приватность не проверялась", "privacy_unreadable": "не удалось проверить приватность", "preview error": "ошибка превью", "Open item for details": "Подробности — на странице видео", "preview…": "превью…", "private_forever": "личное навсегда",
    "Build scene/window clips, rank Best Moments and calculate static 16:9 / 4:5 / 1:1 / 9:16 crop suggestions.":
        "Нарезать видео на сцены, найти лучшие моменты и предложить кадрирование 16:9 / 4:5 / 1:1 / 9:16.", "Archive copy": "Копия в архиве",
    # codes the Library item page shows as values (quality / rights reasons)
    "technical_ok": "технически в порядке", "dark": "тёмное", "very_dark": "очень тёмное", "bright": "светлое",
    "very_bright": "пересвечено", "low_detail": "мало деталей", "very_low_detail": "очень мало деталей",
    "quality_disabled": "проверка качества выключена", "quality_not_run": "качество не проверялось",
    "video_decode_failed": "видео не читается",
    "video_decode_timeout": "видео читается слишком долго", "quality_metrics_failed": "не удалось оценить качество",
    "auto: publishing rights not reviewed": "авто: права на публикацию не проверены",
    "auto: audio track present; publishing rights not reviewed": "авто: есть звук; права на публикацию не проверены",
    "auto: audio/metadata may indicate a performance or show; review music, performance and venue permissions before publishing":
        "авто: по звуку или данным файла похоже на концерт или шоу; перед публикацией проверь права на музыку, выступление и место",
    "Triage only — not a legal determination. Manual tags are never overwritten by automatic analysis.":
        "Только подсказка, не юридическое решение. Ручные отметки анализ не перезаписывает.",
    "no": "нет", "yes": "да", "video": "видео", "photo": "фото", "unknown": "неизвестно", "unreviewed": "не проверено", "not_imported": "не импортировано",
    "SHA-256": "SHA-256",
    "Local visual similarity / M7": "Похожие кадры (на компьютере)", "Reference": "Образец",
    "Perceptual comparison uses cached local thumbnails only. Nothing is uploaded.": "Сравнение по миниатюрам на компьютере. Ничего не отправляется.",
    # ---- devices, cloud
    "Devices": "Устройства",
    "Media-source devices and the future Social Device Lab are separate capabilities. Nothing here hard-codes a personal phone model or account.":
        "Устройства-источники и будущая проверка публикаций — разные вещи. Никакие личные телефоны и аккаунты здесь не прописаны.",
    "Android · Media Source": "Android · источник видео", "Existing ADB/MediaStore ingest foundation.": "Загрузка с Android через ADB.",
    "Android · Social Device Lab": "Android · проверка публикаций", "Planned for native QA, draft handoff and manual fallback.": "Запланировано.",
    "Not represented as implemented until real-device validation passes.": "Не считается готовым, пока не проверено на реальном устройстве.",
    "iPhone / iOS": "iPhone / iOS", "Not implemented in this release.": "В этой версии нет.", "Per-install device registry": "Список устройств этой установки",
    "Separate future media-source and Social Device Lab adapters.": "Будущие подключения устройств.", "Media-source recovery": "Если источник пропал",
    "If Android or another local source is missing, recheck discovery. This only rescans source availability; it does not change device settings or delete media.":
        "Если Android или другой источник пропал, проверь заново. Это только ищет источники — ничего не меняет и не удаляет.",
    "Recheck media sources": "Проверить источники заново",
    "Cloud": "Облако", "Optional services": "Необязательные сервисы",
    "Cloud features remain opt-in. Local processing and local media are the default.": "Облако — только по желанию. По умолчанию всё на компьютере.",
    "Cloud Vault": "Облачное хранилище", "Cloud Compute": "Облачные вычисления", "Disabled": "Выключено",
    "Future modes: exports only, selected media, or full archive mirror. Enabling upload must never delete local/source originals.":
        "В будущем: только экспорт, выбранные файлы или весь архив. Загрузка никогда не удаляет файлы на компьютере и оригиналы.",
    "Local · current": "Компьютер · сейчас", "Cloud · planned": "Облако · план", "Auto · planned": "Авто · план",
    "Supabase may coordinate identity/jobs/metadata later; heavy AI/FFmpeg belongs on dedicated workers, not the control plane.":
        "Позже облако может хранить учётную запись и метаданные; тяжёлая обработка — на отдельных серверах.",
    # ---- social lab
    "M10 / Local-first": "Всё на компьютере",
    "Local-first": "Всё на компьютере", "Novelty Guard": "Проверка новизны", "Local history": "История на компьютере",
    "Content Queue": "Очередь публикаций", "Safe fallback": "Безопасный ручной вариант", "Local manifest": "Описание для ручной публикации",
    "Local experiments": "Эксперименты на компьютере", "CSV preview": "Просмотр CSV", "CSV import": "Импорт CSV",
    "Local Search": "Поиск на компьютере", "Local Render": "Сборка на компьютере", "Local visual similarity": "Похожие кадры (на компьютере)",
    "Publication history and structural Novelty Guard are local. No social account is connected and nothing is published automatically.":
        "История публикаций и проверка на повторы — на компьютере. Соцсети не подключены, ничего не публикуется само.",
    "history records": "записей истории", "novelty checks": "проверок на повторы", "experiments": "экспериментов",
    "Rendered compositions": "Готовые монтажи", "No finished local compositions yet.": "Готовых монтажей пока нет.",
    "Content queue": "Очередь публикаций", "Queue is empty.": "Очередь пуста.", "Publication history": "История публикаций",
    "History is empty. A novelty check does not publish anything.": "История пуста. Проверка на повторы ничего не публикует.",
    "Novelty Guard v1": "Проверка на повторы v1",
    "Exact hash + structural overlap + visual_dhash_v1 + local audio_spectrum_v1. Audio alone can request review but cannot block unless another strong similarity signal agrees.":
        "Сравнивает файлы, структуру, картинку и звук. Один только звук может попросить проверку, но не блокирует.",
    "M11 Experiments": "Эксперименты", "Open Experiments": "Открыть эксперименты",
    "Plan hook/caption/cover/duration/order variants and record manual/import performance metrics locally.":
        "Планируй варианты начала, подписи, обложки, длины и порядка и записывай результаты на компьютере.",
    "M12 Manual Handoff": "Ручная передача", "Open Manual Handoff": "Открыть ручную передачу",
    "Create a local manifest for manual upload. No provider API, token or automatic publishing is used.":
        "Создаёт файл-описание для ручной загрузки. Никаких ключей и автопубликаций.",
    "Privacy boundary:": "Граница приватности:",
    "Publication history and detailed novelty signals stay in the local MediaEngine database. No raw media or fingerprints are sent to Supabase.":
        "История публикаций и данные проверок остаются в базе на компьютере. Видео и отпечатки никуда не отправляются.",
    "Experiments": "Эксперименты", "M11 / Local experiments": "Эксперименты на компьютере",
    "Plan metadata variants and record manual/import performance results locally. No social account or publishing connector is used.":
        "Планируй варианты и записывай результаты на компьютере. Соцсети не используются.",
    "Experiment title": "Название эксперимента", "Objective / hypothesis": "Цель / гипотеза", "Create": "Создать",
    "No experiments yet.": "Экспериментов пока нет.", "Back to Social Lab": "Назад в Social Lab",
    "Experiment": "Эксперимент", "M11 / Experiment": "Эксперимент", "Add variant": "Добавить вариант", "Record manual result": "Записать результат вручную",
    "Derived metric summaries": "Сводка показателей", "Descriptive totals and rates only. MediaEngine does not rank variants or choose a winner.":
        "Только суммы и доли. Программа не ранжирует варианты и не выбирает победителя.",
    "CSV import preview": "Предпросмотр импорта CSV",
    "Required: variant_id plus at least one metric column. Preview never writes data; confirm import is a separate step. Max 200 rows / 128 KiB.":
        "Нужно: variant_id и хотя бы один столбец с показателем. Предпросмотр ничего не записывает; импорт — отдельным шагом. До 200 строк / 128 КБ.",
    "Validate & preview": "Проверить и показать", "Back to Experiments": "Назад к экспериментам", "Variant label": "Название варианта",
    "Hook": "Начало", "Caption": "Подпись", "Cover ref": "Обложка", "Duration s": "Длительность, с", "Clip order: 3,2,1": "Порядок клипов: 3,2,1",
    "Views": "Просмотры", "Likes": "Лайки", "Comments": "Комментарии", "Shares": "Репосты", "Saves": "Сохранения", "Avg view s": "Средний просмотр, с",
    "3s retention %": "Удержание 3 с, %", "Completion %": "Досмотры, %",
    "Manual social handoff": "Ручная передача в соцсети", "M12 / Safe fallback": "Безопасный ручной вариант",
    "Generate a local JSON manifest beside your workflow. MediaEngine does not upload media, call a provider API or use credentials.":
        "Создаёт JSON-описание на компьютере. Программа не загружает видео и не использует пароли.",
    "No automatic publishing.": "Никаких автопубликаций.", "Caption / notes": "Подпись / заметки", "Create local handoff manifest": "Создать описание для передачи",



    # ---- jobs and background work messages
    "Started": "Начало", "· Finished": "· Конец", "Finished": "Готово", "Cancelled by user": "Ты отменил сборку", "Cancelled": "Отменено",
    "Media Brain failed": "Анализ не удался", "Retry failed": "Повторить неудачные", "Discovering": "Ищу", "Discovery finished": "Поиск закончен",
    "Discovery paused while a foreground job is running": "Поиск на паузе, пока идёт задача", "Idle": "Ожидание", "Excluded": "Исключено",
    "Analyzing local/staged files": "Анализирую файлы", "Archiving": "Архивирую", "Building virtual clips + Smart Crop": "Создаю клипы и кадрирование",
    "Conversion cancelled": "Конвертация отменена", "Conversion interrupted by app restart. Start it again.": "Конвертация прервана перезапуском. Запусти снова.",
    "Converter stalled; restarting MediaEngine automatically…": "Конвертация зависла; перезапускаю программу…", "Importing selected files": "Импортирую выбранные файлы",
    "Moving rejected staging copies to quarantine": "Переношу отклонённые копии в карантин", "Moving/marking private items": "Отмечаю личное",
    "Resuming conversion after restart…": "Продолжаю конвертацию после перезапуска…", "Unknown job kind": "Неизвестный тип задачи",
    "Cancelling after current operation…": "Отменю после текущего шага…", "Job stalled repeatedly; restarting MediaEngine automatically…": "Задача несколько раз зависла; перезапускаю программу…",
    "Process stalled; restarting automatically…": "Процесс завис; перезапускаю…", "Stopped after automatic recovery attempts": "Остановлено после попыток восстановления",
    # ---- filter / sort options
    "All accessible videos": "Все доступные видео", "All local sources": "Все источники на компьютере", "All source items": "Все файлы источников",
    "All sources": "Все источники", "Any origin": "Любой источник", "Any privacy state": "Любая приватность", "Any rights state": "Любые права",
    "By source: all": "Источник: все", "Existing local": "Уже на компьютере", "From Android": "С Android", "From SD/USB": "С SD/USB",
    "Library only": "Только библиотека", "Local folders": "Папки на компьютере", "Not in Library": "Не в библиотеке",
    "Name": "Имя", "Newest": "Сначала новые", "Oldest": "Сначала старые", "Largest": "Сначала большие", "Smallest": "Сначала маленькие",
    "Longest": "Сначала длинные", "Photos": "Фото", "Photos + videos": "Фото и видео", "Privacy safe": "Приватность: безопасно",
    "Quality score": "Оценка качества", "Duplicate": "Дубль", "Rights cleared": "Права: чисто", "Rights flagged": "Права: есть вопросы",
    "Rights unknown": "Права: неизвестно", "Review rights": "Проверить права", "Reset rights status": "Сбросить права", "Rights…": "Права…",
    "Cleared": "Чисто", "Do not publish": "Не публиковать", "Permission needed": "Нужно разрешение", "Unknown": "Неизвестно",
    "General": "Общий", "Car / dashboard": "Машина / видеорегистратор", "Other / manual": "Другое / вручную",
    "Original framing": "Исходный кадр", "Choose rendered composition": "Выбери готовый монтаж", "No base composition": "Без основы",
    # ---- status words (badges, job stages, states) - whole text only
    "in-library": "в библиотеке", "source": "источник", "archived": "в архиве", "imported": "импортировано", "local": "на компьютере",
    "importing": "импортирую", "not_imported": "не импортировано", "skipped_duplicate": "пропущено (дубль)", "rejected": "отклонено",
    "private": "личное", "duplicate": "дубль", "review": "на проверку", "safe": "безопасно", "pending": "ждёт", "analyzing": "анализ",
    "analyzed": "проанализировано", "error": "ошибка", "queued": "в очереди", "running": "идёт", "done": "готово", "failed": "ошибка",
    "cancelled": "отменено", "canceled": "отменено", "interrupted": "прервано", "skipped": "пропущено", "finished": "готово",
    "import": "импорт", "analyze": "анализ", "import_analyze": "импорт и анализ", "media_brain": "анализ видео", "archive": "архив",
    "reject": "отклонение", "convert": "конвертация", "converting": "конвертирую", "resuming": "продолжаю", "watchdog_retry": "повтор",
    "watchdog_app_restart": "перезапуск", "starting": "запуск", "good": "хорошее", "ok": "нормальное", "poor": "слабое",
    "clear": "чисто", "permission": "нужно разрешение", "blocked": "заблокировано", "unknown": "неизвестно", "unreviewed": "не проверено",
    "selected": "выбрано", "staged": "в Staging", "new": "новое", "ready": "готово", "rendered": "собран", "rendering": "собираю",
    "draft": "черновик", "missing": "нет", "available": "доступно", "video": "видео", "image": "фото", "photo": "фото", "audio": "звук",
    # ---- messages put on the page by scripts (toasts, progress, statuses)
    "Select files first": "Сначала выбери файлы", "Select local videos first": "Сначала выбери видео", "Done": "Готово",
    "Choose a rights tag": "Выбери отметку прав", "Rights updated": "Права обновлены", "Previews status unavailable": "Состояние превью недоступно",
    "Select at least one video": "Выбери хотя бы одно видео", "Choose a preset first": "Сначала выбери пресет", "Could not start": "Не удалось запустить",
    "Conversion started": "Конвертация запущена", "choose preset": "выбери пресет", "Estimate appears after you choose videos and a preset.":
        "Оценка появится, когда выберешь видео и пресет.", "No compression preset is selected yet.": "Пресет ещё не выбран.",
    "Rechecking…": "Проверяю…", "Source recheck started": "Проверка источников запущена", "open Help & Recovery": "открой «Помощь и восстановление»",
    "status unavailable": "состояние недоступно", "MediaEngine is closed. You can close this window.": "MediaEngine закрыт. Окно можно закрыть.",
    "MediaEngine is taking longer than expected. Start it again from the desktop shortcut; startup health-check will roll back a bad release.":
        "MediaEngine запускается дольше обычного. Запусти его снова с ярлыка; если новая версия не поднимется, вернётся прежняя.",
    "Preview generation is temporarily unavailable for this file. MediaEngine will retry later.": "Превью для этого файла пока не получилось. Программа попробует позже.",
    "No folder chosen. You can also paste the path.": "Папка не выбрана. Можно вставить путь вручную.", "No folder chosen.": "Папка не выбрана.",
    "No videos chosen.": "Видео не выбраны.", "Build or save a trajectory first": "Сначала построй или сохрани траекторию",
    "Clip or crop plan not found": "Клип или план кадрирования не найден", "Local video file is unavailable": "Видеофайл на компьютере недоступен",
    "No files selected": "Файлы не выбраны", "Unknown action": "Неизвестное действие",
    "Discovery": "Поиск", "Discovery started": "Поиск запущен", "Saved": "Сохранено", "Copied": "Скопировано",
    "Blocked Novelty Guard items cannot generate a handoff. Similar-review items require this explicit manual action.":
        "Заблокированные проверкой на повторы ролики передать нельзя; похожие — только вручную.",
    "No library jobs yet.": "Задач библиотеки пока нет.", "Reel builds (Auto Edit)": "Сборки роликов (автомонтаж)",
    "s": "сек",          # the unit after a time field ("from [0.0] to [5.5] s")
    # file sizes ("16.8 MB"): looked up through ⟦unit:…⟧ by the patterns below, never matched as page text
    # deep audit 2026-10-14: job and error messages
    'The AI found no usable moments in these videos. Press Retry; if it repeats, build without AI.': 'ИИ не нашёл подходящих моментов в этих видео. Нажми «Повторить»; если повторится — собери без ИИ.',
    'A moment could not be cut from one of the videos. Press Retry; if it repeats, build without AI.': 'Не получилось вырезать момент из одного из видео. Нажми «Повторить»; если повторится — собери без ИИ.',
    'The final video could not be put together. Press Retry; if it repeats, free the cache of this project.': 'Не получилось склеить итоговое видео. Нажми «Повторить»; если повторится — очисти кэш этого проекта.',
    'The finished reel could not be read back for the check. Press Retry; if it repeats, free the cache of this project.': 'Готовый ролик не удалось прочитать для проверки. Нажми «Повторить»; если повторится — очисти кэш этого проекта.',
    'A moment could not be prepared. Press Retry; if it repeats, free the cache of this project.': 'Не получилось подготовить момент. Нажми «Повторить»; если повторится — очисти кэш этого проекта.',
    'A trimmed moment could not be cut. Check its times or let MediaEngine choose again.': 'Не получилось вырезать обрезанный момент. Проверь время или дай MediaEngine выбрать заново.',
    'The same moment was chosen twice. Choose another one.': 'Один и тот же момент выбран дважды. Выбери другой.',
    'The reel came out in a wrong size. Press Retry; if it repeats, free the cache of this project.': 'Ролик получился не того размера. Нажми «Повторить»; если повторится — очисти кэш этого проекта.',
    'The finished reel could not be saved correctly. Check the free space and press Retry.': 'Готовый ролик не удалось правильно сохранить. Проверь свободное место и нажми «Повторить».',
    'This theme is not available. Choose another one.': 'Эта тема недоступна. Выбери другую.',
    'The finished reel could not be saved correctly. Press Retry.': 'Готовый ролик не удалось правильно сохранить. Нажми «Повторить».',
    'The reel could not be built. Press Retry; if it repeats, build without AI or free the cache of this project.': 'Ролик не получилось собрать. Нажми «Повторить»; если повторится — собери без ИИ или очисти кэш этого проекта.',
    'Accept a revision before exporting': 'Сначала прими версию',
    'Export verification failed': 'Проверка сохранённого файла не прошла — попробуй ещё раз',
    'No exact AI+ model there (vision_model_int8.onnx, text_model_int8.onnx, vocab.json, merges.txt).': 'Там нет точной модели ИИ+ (vision_model_int8.onnx, text_model_int8.onnx, vocab.json, merges.txt).',
    'Not enough free disk space for the AI model.': 'Недостаточно места на диске для модели ИИ.',
    'Unknown theme': 'Неизвестная тема',
    'Convert up to 50 videos at once': 'Можно конвертировать до 50 видео за раз',
    'Could not read video duration': 'Не удалось прочитать длительность видео',
    'FFmpeg is not available': 'FFmpeg недоступен',
    'None of the selected videos can be converted (private, rejected or removed)': 'Ни одно из выбранных видео нельзя конвертировать (личное, отклонено или убрано)',
    'Target size must be between 50 MB and 100000 MB': 'Размер должен быть от 50 МБ до 100000 МБ',
    'Unknown preset': 'Неизвестный пресет',
    'interrupted_by_restart': 'прервано перезапуском программы',
    'ADB is not installed or not found': 'ADB не установлен или не найден',
    'Archive copy verification failed': 'Проверка копии в архиве не прошла',
    'Archive verification failed': 'Проверка архива не прошла',
    'Catalog item missing': 'Запись в каталоге не найдена',
    'Copy verification failed: SHA-256 mismatch': 'Проверка копии не прошла: файлы различаются',
    'Cross-volume move verification failed': 'Проверка переноса на другой диск не прошла',
    'File is not local. Import it first.': 'Файла нет на этом компьютере (диск отключён?) — подключи диск или сначала импортируй файл.',
    'Imported local copy is missing': 'Копия файла на компьютере пропала',
    'Invalid rights status': 'Неверный статус прав',
    'Local source file is unavailable': 'Исходный файл недоступен (диск отключён?)',
    'Media Brain v1 currently works on video': 'Поиск моментов работает только с видео',
    'Move verification failed: size mismatch': 'Проверка переноса не прошла: размер не совпадает',
    'No failed items to retry': 'Нет файлов с ошибкой для повтора',
    'No local file available': 'Файл недоступен на этом компьютере',
    'Private item cannot be archived to main library': 'Личный файл нельзя положить в общий архив',
    'SD/USB source file is unavailable': 'Файл на карте или USB-диске недоступен (носитель отключён?)',
    'Unknown rights preset': 'Неизвестная метка прав',
    'launcher unavailable': 'не удалось перезапустить программу',
    'watchdog_exhausted': 'задача несколько раз зависла и остановлена',
    'Added. The files stay in their folder — keep that disk connected.': 'Добавлено. Файлы остаются в своей папке — не отключай этот диск.',
    'Import complete — source can be disconnected': 'Импорт готов — источник можно отключить',
    'New versions are made from the others.': 'Новые версии собираются из остальных.',
    'not found (moved or deleted)': 'не найден (перемещён или удалён)',
    'no video': 'нет видео', 'too short': 'слишком короткое',
    "unit:B": "Б", "unit:KB": "КБ", "unit:MB": "МБ", "unit:GB": "ГБ", "unit:TB": "ТБ",
}

APP_PATTERNS: list[tuple[str, str]] = [
    (r"One reel can use up to (\d+) videos\. Selected:", r"В один ролик помещается до \1 видео. Выбрано:"),
    (r"Make (\d+) reels", r"Сделать роликов: \1"),
    (r"Days with more than (\d+) videos are left out \(tick their videos below\):", r"Дни, где больше \1 видео, пропущены (их видео можно отметить ниже):"),
    (r"The folder is not available: (.+)", r"Папка недоступна: \1"),
    ('Import finished with (\\d+) error\\(s\\) — keep the source connected', 'Импорт закончен, ошибок: \\1 — не отключай источник'),
    ('Analyzing (\\d+) local file\\(s\\); (\\d+) import error\\(s\\) — keep the source connected\\.', 'Анализирую файлы: \\1; ошибок импорта: \\2 — не отключай источник.'),
    ('Analyzing (\\d+) file\\(s\\) where they are — keep that disk connected\\.', 'Анализирую файлы на месте: \\1 — не отключай этот диск.'),
    ('Import complete — source can be disconnected\\. Analyzing (\\d+) local file\\(s\\)\\.', 'Импорт готов — источник можно отключить. Анализирую файлы: \\1.'),
    ('Finished with (\\d+) error\\(s\\)', 'Готово, ошибок: \\1'),
    ('Some videos of this reel are not there any more \\(moved or deleted\\): (\\d+) of (\\d+)\\.', 'Некоторых видео этого ролика больше нет на месте (перемещены или удалены): \\1 из \\2.'),
    ('No connection to huggingface\\.co\\. Check the internet connection and try again\\. \\[(.*)\\]', 'Нет связи с huggingface.co. Проверь интернет и попробуй ещё раз. [\\1]'),
    ('No exact FAST_LOCAL model found there \\((.*)\\)', 'Там нет точной модели ИИ (\\1)'),
    ('Not enough free disk space for the AI\\+ model \\(about ([\\d.]+) GB needed\\)\\.', 'Недостаточно места на диске для модели ИИ+ (нужно около \\1 ГБ).'),
    ('A downloaded file is not the exact model file \\((.*)\\)\\. Try again\\.', 'Скачанный файл не совпадает с моделью (\\1). Попробуй ещё раз.'),
    (r"Ready for (\d+) of (\d+) video\(s\)\.", r"Готово для \1 из \2 видео."),
    (r"Search ready for (\d+) of (\d+) video\(s\)\.", r"Поиск готов для \1 из \2 видео."),
    (r"Reels ready for (\d+) of (\d+) video\(s\)\.", r"Для роликов готово \1 из \2 видео."),
    (r"AI\+ preparation failed: (.*)", r"Подготовка ИИ+ не удалась: \1"),
    (r"The best (\d+) of (\d+) are shown\.", r"Показаны лучшие \1 из \2."),
    (r"AI\+ speed on this PC: (\d+)\.(\d+) s per frame\. The first analysis looks at up to 48 frames of each video \(about one per second\): "
     r"about (\d+) s for a video of a minute or longer\. Later builds reuse it\.",
     r"Скорость ИИ+ на этом компьютере: \1,\2 с на кадр. При первом анализе модель смотрит до 48 кадров каждого видео (примерно "
     r"один в секунду): около \3 с на видео длиной от минуты. Следующие сборки используют этот анализ."),
    (r"(\d+) video\(s\) match the theme, best first\. Open one to start at its best moment\.",
     r"Подходящих видео: \1, лучшие первыми. Открой видео — оно начнётся с лучшего момента."),
    (r"Only (\d+) of (\d+) video\(s\) are prepared for the search\.", r"Для поиска подготовлено только \1 из \2 видео."),
    (r"Prepare the rest", r"Подготовь остальные"), (r"on the Library page\.", r"на странице «Библиотека»."),
    (r"The search needs preparing again \(new themes\)\.", r"Поиск нужно подготовить заново (новые темы)."),
    (r"Not enough free disk space for the AI\+ model \(about ([\d.]+) GB needed\)\.", r"Мало места на диске для модели ИИ+ (нужно около \1 ГБ)."),
    (r"A downloaded file is not the exact model file \((.+)\)\. Try again\.", r"Скачанный файл не совпадает с точным файлом модели (\1). Попробуй ещё раз."),
    (r"No connection to huggingface\.co\. Check the internet connection and try again\. \[(.*)\]",
     r"Нет связи с huggingface.co. Проверь интернет и попробуй ещё раз. [\1]"),
    (r"Folder: (.+) \((\d+)\)", r"Папка: \1 (\2)"),
    (r"(very_dark|dark|very_bright|bright),(very_low_detail|low_detail)", r"⟦\1⟧, ⟦\2⟧"),
    (r"Preparing a recording without a length: (.+)", r"Подготовка записи без длины: \1"),
    (r"(\d+) errors?", r"ошибок: \1"), (r"(\d+) GB - less than 6 GB, long 4K videos may be slow", r"\1 ГБ — меньше 6 ГБ, длинные 4K-видео могут обрабатываться медленно"),
    (r"(\d+) GB", r"\1 ГБ"), (r"([\d.]+) GB - less than 5 GB, builds may fail", r"\1 ГБ — меньше 5 ГБ, сборка может не пройти"), (r"Credentials: ([a-z_]+)", r"Пароли: ⟦\1⟧"),
    (r"(\d+) folder source\(s\) configured", r"источников-папок: \1"),
    (r"v(\d+\.\d+\.\d+[\w.-]*)( b\d+)?", r"v\1\2"),
    (r"MediaEngine v(\d+\.\d+\.\d+[\w.-]*)( b\d+)?", r"MediaEngine v\1\2"),
    (r"(\d+) matching catalog videos · local availability is checked only for the current page\.", r"Найдено видео: \1 · доступность проверяется только на этой странице."),
    (r"(\d+) selected", r"выбрано: \1"), (r"(\d+) SD/USB mounted", r"SD/USB подключено: \1"), (r"(\d+) local folder\(s\)", r"папок: \1"),
    (r"of (\d+)", r"из \1"),
    (r"(\d+) local item\(s\)\. This is the media already selected/imported and available for work\.", r"В библиотеке: \1. Это то, что уже выбрано и доступно для работы."),
    (r"best ([\d.]+)", r"лучшее \1"), (r"good ([\d.]+)", r"хорошее \1"), (r"ok ([\d.]+)", r"нормальное \1"), (r"weak ([\d.]+)", r"слабое \1"),
    (r"detail ([\d.]+) · exposure ([\d.]+) · motion ([\d.]+) · center ([\d.]+)", r"детали \1 · экспозиция \2 · движение \3 · центр \4"),
    (r"([\d:]+)–([\d:]+) · ([\d.]+)s · score ([\d.]+) · best", r"\1–\2 · \3 с · оценка \4 · лучшее"),
    (r"([\d:]+)–([\d:]+) · ([\d.]+)s · score ([\d.]+) · good", r"\1–\2 · \3 с · оценка \4 · хорошее"),
    (r"([\d:]+)–([\d:]+) · ([\d.]+)s · score ([\d.]+) · ok", r"\1–\2 · \3 с · оценка \4 · нормальное"),
    (r"([\d:]+)–([\d:]+) · ([\d.]+)s · score ([\d.]+) · (\w+)", r"\1–\2 · \3 с · оценка \4 · \5"),
    (r"(\d+) virtual clips\. Use Open clip to play only that interval and preview its Smart Crop\.", r"Виртуальных клипов: \1. «Открыть клип» играет только этот отрезок."),
    (r"(\d+) preview frames", r"кадров превью: \1"),
    (r"(16:9|9:16|1:1|4:5) · not rendered", r"\1 · не собран"), (r"(16:9|9:16|1:1|4:5) · (\d+) clips · draft", r"\1 · клипов: \2 · черновик"),
    (r"(16:9|9:16|1:1|4:5) · (\d+) clips · rendered", r"\1 · клипов: \2 · собран"), (r"(16:9|9:16|1:1|4:5) · (\d+) clips · (\w+)", r"\1 · клипов: \2 · \3"),
    (r"variants · (\d+) result rows", r"вариантов · строк результатов: \1"),
    (r"(draft|planned|published) · duration (.+) · order (.+)", r"⟦\1⟧ · длительность \2 · порядок \3"), (r"(\d+) results?", r"результатов: \1"),
    (r"Hook: (.*) · Caption: (.*) · Cover: (.*)", r"Начало: \1 · Подпись: \2 · Обложка: \3"),
    (r"(\d+) rows · (\d+) views · (\d+) engagements", r"строк: \1 · просмотров: \2 · реакций: \3"),
    (r"ER (.*) · avg (.*) · 3s (.*) · completion (.*)", r"ER \1 · средн. \2 · 3 с \3 · досмотры \4"),
    (r"(16:9|9:16|1:1|4:5) Smart Crop", r"\1 умное кадрирование"),
    (r"Job #(\d+)", r"Задача №\1"), (r"Job (\d+)", r"Задача \1"), (r"Converter job #(\d+)", r"Конвертация №\1"), (r"· Elapsed (\d+)s", r"· Длительность \1 с"),
    (r"· Elapsed (\d+)m (\d+)s", r"· Длительность \1 мин \2 с"), (r"· Elapsed (\d+)h (\d+)m", r"· Длительность \1 ч \2 мин"),
    (r"· Elapsed (.+)", r"· Длительность \1"),
    (r"Converted (\d+) files?", r"Сконвертировано: \1"), (r"Converted (\d+); failed (\d+)", r"Сконвертировано: \1; ошибок: \2"),
    (r"([a-z_]+) · ([a-z_]+) · (\d+/\d+) · (.+)", r"⟦\1⟧ · ⟦\2⟧ · \3 · \4"),
    (r"(\d+)/(\d+) · (\d+)% · (\d+) errors?", r"\1/\2 · \3% · ошибок: \4"),
    (r"Rights updated for (\d+) item\(s\)", r"Права обновлены: \1"), (r"Discovery error: (.*)", r"Ошибка поиска: \1"),
    (r"Analyzing local copy: (.*)", r"Анализирую копию: \1"), (r"Analyzing (.*)", r"Анализирую \1"), (r"Archiving (.*)", r"Архивирую \1"),
    (r"Checking duplicate before transfer: (.*)", r"Проверяю на дубль: \1"), (r"Converting (\d+)/(\d+) · (\d+)% · (.*)", r"Конвертирую \1/\2 · \3% · \4"),
    (r"Converting (\d+)/(\d+) · (.*)", r"Конвертирую \1/\2 · \3"), (r"Importing (.*)", r"Импортирую \1"), (r"Job crashed: (.*)", r"Задача упала: \1"),
    (r"Media Brain: (.*)", r"Анализ: \1"), (r"Preparing (\d+) video\(s\)…", r"Готовлю видео: \1…"), (r"Skipped missing local file: (.*)", r"Пропущен отсутствующий файл: \1"),
    (r"Converter stalled; process restarted automatically · (\d+)/(\d+)", r"Конвертация зависла; процесс перезапущен · \1/\2"),
    (r"(\d+(?:\.\d+)?) s", r"\1 с"), (r"· (\d+(?:\.\d+)?) s", r"· \1 с"), (r"(\d+) s · recommended", r"\1 с · рекомендуется"),
    (r"Job #(\d+) · (.+)", r"Задача №\1 · \2"),
    (r"quality (\S+)( [\d.]+)?", r"качество ⟦\1⟧\2"), (r"rights (\S+)", r"права ⟦\1⟧"),
    (r"([\w .()-]{1,40}) connected", r"\1 подключён"), (r"Discovering · (.*)", r"Поиск · \1"), (r"(\d+) found", r"найдено: \1"),
    (r"Updating MediaEngine… current tab will reconnect\.", r"Обновляю MediaEngine… вкладка переподключится сама."),
    (r"Restarting MediaEngine… current tab will reconnect\.", r"Перезапускаю MediaEngine… вкладка переподключится сама."),
    (r"SOURCE SAFE TO DISCONNECT · (.*)", r"ИСТОЧНИК МОЖНО ОТКЛЮЧИТЬ · \1"), (r"(.*) · (\d+) error\(s\)", r"\1 · ошибок: \2"),
    (r"ERROR: (.*)", r"ОШИБКА: \1"), (r"(\d+)/(\d+) clips", r"\1/\2 клипов"),
    (r"(\d+) videos? · ([\d.]+ [KMGT]?B) · choose a preset", r"видео: \1 · \2 · выбери пресет"),
    (r"(\d+) videos? · ([\d.]+ [KMGT]?B) → target ≤ ([\d.]+ [KMGT]?B) total", r"видео: \1 · \2 → не больше \3 всего"),
    (r"(\d+) videos? · ([\d.]+ [KMGT]?B) → estimated ≈ ([\d.]+ [KMGT]?B)", r"видео: \1 · \2 → примерно \3"),
    (r"([\d.]+) MB per file · save up to ([\d.]+ [KMGT]?B)( / \d+%)?\.", r"\1 МБ на файл · экономия до \2\3."),
    (r"Estimated saving ([\d.]+ [KMGT]?B)( / \d+%)? · actual size can vary by about 20–30%\.", r"Экономия примерно \1\2 · реальный размер может отличаться на 20–30%."),
    (r"Estimated saving ([\d.]+ [KMGT]?B)( / \d+%)? · refining from video duration…", r"Экономия примерно \1\2 · уточняю по длительности видео…"),
    (r"Estimated output may be larger than source · actual size can vary by about 20–30%\.", r"Результат может быть больше исходника · размер может отличаться на 20–30%."),
    (r"Estimated output may be larger than source · refining from video duration…", r"Результат может быть больше исходника · уточняю по длительности видео…"),
    (r"(\d+) frames", r"кадров: \1"), (r"(\d+)/(\d+) frames", r"кадров: \1 из \2"),
    (r"(\d+) clips · (\d+) best", r"клипов: \1 · лучших: \2"),
    (r"(\d+)% similar", r"похоже на \1%"), (r"Previews (\d+)/(\d+)", r"Превью \1/\2"), (r"Previews (\d+)/(\d+) unavailable", r"Превью \1/\2 недоступно"),
    (r"Previews (\d+)/(\d+) loading", r"Превью \1/\2 загружаются"),
    (r"Creating durable job for (\d+) selected files…", r"Создаю задачу для выбранных файлов: \1…"),
    (r"Job #(\d+) accepted\.?", r"Задача №\1 принята"), (r"Could not start source recheck — (.*)", r"Не удалось запустить проверку источников — \1"),
    (r"HTTP (\d+)", r"HTTP \1"),

    (r"More than (\d+) videos chosen\. One reel can use up to (\d+)\.", r"Выбрано больше \1 видео. В один ролик можно взять до \2."),
    (r"· (\d+) s · (\d{4}-\d\d-\d\d \d\d:\d\d)", r"· \1 с · \2"),   # reel builds on the Jobs page
    (r"(\d+(?:\.\d+)?) (B|KB|MB|GB|TB)", r"\1 ⟦unit:\2⟧"),   # a size on its own ("155.4 GB")
    (r"(.+[.!?]) \[(.+)\]", r"⟦\1⟧ [\2]"),   # a friendly error with its code
]

APP_JS: dict[str, str] = {
    "Quit MediaEngine? Running work stops; you can start it again from the desktop shortcut.":
        "Закрыть MediaEngine? Текущая работа остановится; запустить снова можно с ярлыка.",
    "Work is running.": "Идёт работа.", "A job is running.": "Идёт задача.",
    "\\n\\nQuit anyway? It will be marked interrupted and can be retried.": "\\n\\nВсё равно выйти? Работа будет отмечена как прерванная, её можно повторить.",
    "\\n\\nRestart/update anyway? The current file may need to restart.": "\\n\\nВсё равно перезапустить? Текущий файл, возможно, начнётся заново.",
    "Mark selected Private forever?": "Отметить выбранное как личное навсегда? Оно уйдёт из библиотеки и никогда не попадёт в ролики.",
    "Archive selected local/staged files? Source-device originals are never deleted.": "Отправить выбранное в архив? Оригиналы на устройствах никогда не удаляются.",
    "Move selected Staging copies to Rejected quarantine and hide them? Phone/SD originals stay untouched.":
        "Перенести выбранные копии из Staging в карантин Rejected и скрыть? Оригиналы на телефоне/SD не трогаются.",
    "Remove selected items from Library? Imported Staging copies move to the Rejected / Removed from Library folder (delete them there when you are sure). Source originals and local/archive files stay untouched.":
        "Убрать выбранное из библиотеки? Копии из Staging переносятся в папку Rejected / Removed from Library (удали их там, когда будешь уверен). Оригиналы и файлы в папках/архиве не трогаются.",
    "Remove this item from Library? Its imported Staging copy moves to the Rejected / Removed from Library folder (delete it there when you are sure); the source original stays untouched.":
        "Убрать из библиотеки? Копия из Staging переносится в папку Rejected / Removed from Library (удали её там, когда будешь уверен); оригинал не трогается.",
}

# Auto Edit pages (phrase-inside-text mode): counted nouns, before the phrase replacements; ⟪n|1|2-4|5+⟫ = plural
APP_COUNT_SUBS: list[tuple[str, str]] = [
    (r"\b(\d+) revision\(s\)", r"\1 ⟪\1|версия|версии|версий⟫"),
    (r"\b(\d+) usable video\(s\)", r"\1 ⟪\1|пригодное видео|пригодных видео|пригодных видео⟫"),
    (r"\b(\d+) chosen video\(s\)", r"\1 ⟪\1|выбранное видео|выбранных видео|выбранных видео⟫"),
    (r"\b(\d+) video file\(s\) in folder", r"\1 видео в папке"),
    (r"\b(\d+) overlapping moment\(s\) of the same video were left out so nothing repeats",
     r"\1 ⟪\1|пересекающийся момент одного видео убран|пересекающихся момента одного видео убраны|пересекающихся моментов одного видео убраны⟫, чтобы ничего не повторялось"),
    (r"\b(\d+) skipped\b", r"\1 ⟪\1|пропущено|пропущено|пропущено⟫"),
    (r"\b(\d+) videos in this folder\.", r"В этой папке \1 видео."),
    (r"\b(\d+) logical cores\b", r"\1 ⟪\1|логическое ядро|логических ядра|логических ядер⟫"),
    (r"\bRequested (\d+) s, got ([\d.]+) s:", r"Выбрано \1 с, получилось \2 с:"),
]


# Auto Edit pages: sizes inside longer texts ("… · 16.8 MB"), after the phrase replacements so a phrase that
# contains a size ("at least 1 GB") is still matched as a whole first
APP_UNIT_SUBS: list[tuple[str, str]] = [
    (r"\b(\d+(?:\.\d+)?) (B|KB|MB|GB|TB)\b", r"\1 ⟦unit:\2⟧"),
]
