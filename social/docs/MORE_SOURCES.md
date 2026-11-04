# CODEX_03: USA.gov и помощь студентам

Добавлены три адаптера двух новых типов источников: HTML USA.gov, HTML Federal
Student Aid и JSON College Scorecard. Новые модули используют только стандартную
библиотеку Python 3.11. Ядро, его допуск и JSON-контракт не изменялись.

Все команды ниже выполняются из `social/`, кроме явно указанной проверки из корня.

## Полностью офлайн

```sh
python -m socialreel source --source usagov --page energy --fixture fixtures/usagov_energy_synthetic.html --out runs/source-energy
python -m socialreel source --source studentaid --page pell --fixture fixtures/studentaid_pell_synthetic.html --out runs/source-pell
python -m socialreel source --source scorecard --college-id 999001 --fixture fixtures/scorecard_synthetic.json --out runs/source-scorecard
python -m socialreel topics --sources usagov,studentaid,scorecard --fixture fixtures/public_sources_synthetic.json --out runs/public-topics --as-of 2026-11-04
python -m socialreel source --topics runs/public-topics/topics.json --topic-id usagov:wages --out runs/source-wages-replayed
```

Fixture-файлы с суффиксом `synthetic` явно синтетические: они проверяют механизм,
а не текущие правила программ. В офлайн-режиме ключ Scorecard не нужен. Если
manifest не содержит fixture для выбранного источника, запуск завершается ошибкой;
запасного обращения к интернету нет. Относительные пути в manifest считаются от
его папки. Для объединения с прежним Grants.gov добавьте `grants` в `--sources`;
поле `grants_fixture` в готовом manifest указывает на существующий исторический экспорт.

## Живые команды (форматы не проверены)

```sh
python -m socialreel source --source usagov --page energy --out runs/energy-live
python -m socialreel source --source usagov --page wages --out runs/wages-live
python -m socialreel source --source usagov --page unclaimed --out runs/unclaimed-live
python -m socialreel source --source studentaid --page pell --out runs/pell-live
python -m socialreel source --source studentaid --page fafsa_deadlines --out runs/fafsa-live
python -m socialreel topics --sources usagov,studentaid --out runs/public-topics-live
```

`--page` принимает имя из конечного каталога или URL HTTPS на соответствующем
официальном домене. Текущие страницы USA.gov и StudentAid перечислены в модулях
адаптеров; `public_sources_config.json` задаёт, какие из них обходить при поиске тем.
Это небольшой каталог, не поисковик по всему интернету. Его можно переопределить
объектом `public_sources` в `--config`; для Scorecard список ID находится в
`public_sources.scorecard.schools` (по умолчанию пуст).

Для живого Scorecard заранее нужен бесплатный ключ в переменной окружения
`COLLEGE_SCORECARD_API_KEY`. Команда `source --source scorecard --college-id ID
--out DIR` требует настоящий числовой ID выбранного колледжа. Ключ не читается
из JSON/аргумента, не добавляется в URL, квитанции или журнал; передаётся заголовком
`X-Api-Key`. Отсутствующий ключ даёт понятную ошибку до запроса. Ошибки HTTP не
печатают заголовки или текст исключения, который мог бы содержать ключ.

Все живые HTML/API-форматы отмечены **format not checked live**. StudentAid может
вернуть JavaScript-оболочку без текста: адаптер тогда отказывает, не выдумывает
программу и не пытается обходить сайт. HTML ожидается в UTF-8; неизвестная кодировка
не заменяется повреждёнными символами. Редиректы проверяются до перехода на другой
домен. Живые команды и полезность тем в рамках этого задания не проверялись.

## Что сохраняется

`source/` содержит точные байты ответа/fixture и имя с SHA-256. `record.json`
содержит заголовок, URL, полные разделы, кто может обратиться, описание помощи,
способ обращения, условия, найденный текст сроков и сведения о различиях по штатам.
Категории ссылаются на целые разделы и могут пересекаться; это не юридическое
определение подходящих людей. Неизвестные значения остаются `null` или пустым списком.

HTML-разбор выбирает один `main`/`role=main`, иначе один `article`, и заголовок h1.
Скрипты и навигация не становятся фактами. Скрытые панели, примечания и условия
внутри основного текста сохраняются. HTML-сущности декодируются, между абзацами
ставится LF; это явно извлечённый text_content, не исходные HTML-байты. Исходные
байты остаются в снимке. Разделы, включая исключения, не сокращаются и не переводятся.

`claims.json` имеет прежнюю форму: `key`, `statement`, `values`, `source`.
USA.gov не выдаётся за Grants.gov. Текст утверждений копирует полные разделы;
«may» не превращается в обещание. Различия штатов сохраняются при наличии такого
текста, а не приписываются всем программам. Для HTML есть пути элементов и хеш
извлечённого текста, для Scorecard — точный JSON Pointer (плоский или вложенный
ответ), для всех — URL и SHA-256 снимка.

Scorecard сохраняет опубликованные доли получателей Pell Grants и федеральных
кредитов, включая ноль. Это статистика учреждения. Из неё не выводятся право
конкретного человека на помощь, размер выплаты, условия или сроки. Отчётный год
из поля `latest` не угадывается; эти пробелы явно перечислены.

## Темы и то же ядро

Новые источники включаются явно через `topics --sources`. USA.gov получает рубрику
`help_people`, StudentAid/Scorecard — `education`. Используется `social_topics_v2`
с `source_type` и постоянным `topic_id`: например, `usagov:energy`, `studentaid:pell`,
`scorecard:999001`. Их `opportunity_id` равен `null`, а не выдуманному ID Grants.gov.
История может содержать такие ID; баллы объясняют наличие полных разделов и не
измеряют качество или доступность помощи. Смешанный рейтинг — редакторский приоритет.

`source --topics PATH [--topic-id ID]` выбирает тему (по умолчанию первую), сверяет
SHA-256 сохранённого снимка и заново строит утверждения из байтов. Отредактированные
тексты утверждений в `topics.json` не становятся доказательствами. Прежний
`concept_trial.py --topics` принимает только Grants.gov v1: новый формат надо
передавать в `source --topics`, чтобы не подменить тип источника.

Команда сохраняет `concept_inputs.json` через неизменённый `concept_core.inputs`.
`--prepare-request --config PATH` дополнительно вызывает настоящий
`concept_core.build_request`. Конфигурация должна явно содержать прежние разрешения
локального редактора, `hook_language`, `topic_direction` и `unknowns`. Отказ допуска
пишется в `request_status.json`, возвращается код 2; прежний запрос рядом с новыми
данными не остаётся. Модель не запускается, принятие результата не объявляется.

Существующие границы ядра действуют и здесь: полный контекст условий не больше
8192 байт UTF-8, прежние ограничения запроса и проверенный офлайн-токенизатор.
Слишком длинная страница сохраняется целиком в record/claims, затем получает отказ
ядра без обрезки. Автоматическое сокращение источников и обход допуска не добавлены.

## Проверки

Из корня репозитория:

```sh
python -B social/.ci/run_social_concept_core.py
cd social
python -B -m unittest discover -s tests -t .
python -B -m unittest tests.test_usagov tests.test_studentaid -v
```

Офлайн прошли 88 тестов ядра и полный набор 172 теста; новых проверок источников —
30. Для старого полного набора нужны уже предусмотренные Pillow, pypdf и
ffmpeg/ffprobe. Новые тесты запускаются на Python 3.11 без новых зависимостей и
блокируют настоящие сетевые соединения. Проверка построителя запроса останавливается
на границе допуска, не изображая успешную проверку токенизатора или запуск модели.
