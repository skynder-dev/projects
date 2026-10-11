# MIGRATION — перенос проектов обратно в ChatGPT

Снимок: 2026-10-10, вечер (America/Chicago). Основа: `main` на коммите `22e15fa`. Составил Claude (Anthropic) по просьбе владельца.

В этой папке всё, что нужно, чтобы продолжить три проекта репозитория `skynder-dev/projects` в ChatGPT (или в любом другом ассистенте). Ничего в исходных папках проектов (`reveng/`, `forge/`, `social/`) не менялось; здесь только новые файлы и копии документов.

> **Репозиторий публичный.** Всё, что лежит здесь и в других папках, может прочитать любой человек. Ключей, паролей и токенов здесь нет и быть не должно. Секреты GitHub Actions (например, `ANTHROPIC_API_KEY`, о котором говорится в `social/docs/OWNER_REVIEW.md`) в репозитории не хранятся и в новое окружение переносятся вручную владельцем.

## Что внутри

| Путь | Что это |
| --- | --- |
| `README.md` | этот файл: как пользоваться |
| `CHATGPT_PROJECT_INSTRUCTIONS.md` | готовый текст для поля Instructions в ChatGPT Project и три стартовых запроса (по одному на проект) |
| `OWNER_DECISIONS_ALL.md` | все открытые решения владельца по трём проектам в одном списке |
| `reveng/` | **RevEng**: `HANDOFF_FOR_CHATGPT_RU.md` (подробная вводная), `ideas_102.csv` (все 102 идеи), `FILES.md` (карта путей), `docs_snapshot/` (копии ключевых документов) |
| `forge/` | **Merch Forge**: `HANDOFF.md`, `docs_snapshot/` |
| `social/` | **Social** (Reels из Grants.gov): `HANDOFF.md`, `docs_snapshot/` |

Копии в `docs_snapshot/` — снимок на дату выше. Источник правды — папки `reveng/`, `forge/`, `social/` в `main` (их документы обновляются дальше, а снимки нет).

## Как перенести (рекомендуемый порядок)

1. Создайте в ChatGPT **Project** (например, «RevEng / Forge / Social»). Если хотите, по одному Project на проект.
2. В поле **Instructions** вставьте текст из `CHATGPT_PROJECT_INSTRUCTIONS.md` (раздел «Общие инструкции»).
3. Загрузите файлы в Project:
   - для RevEng: `reveng/HANDOFF_FOR_CHATGPT_RU.md`, `reveng/ideas_102.csv`, документы из `reveng/docs_snapshot/`; если есть, ваш исходный `REVENG_CLAUDE_START_PROMPT.md`;
   - для Forge: `forge/HANDOFF.md` и `forge/docs_snapshot/`;
   - для Social: `social/HANDOFF.md` и `social/docs_snapshot/`.
4. Начните первый чат с соответствующего **стартового запроса** из `CHATGPT_PROJECT_INSTRUCTIONS.md`.
5. Если у ChatGPT есть доступ к GitHub (коннектор) или к вебу, дайте ему адрес репозитория: `https://github.com/skynder-dev/projects` (ветка `main`). Для чтения отдельных файлов подходят ссылки вида
   `https://raw.githubusercontent.com/skynder-dev/projects/main/<путь>`.
   Весь репозиторий одним архивом (около 34 МБ): `https://github.com/skynder-dev/projects/archive/refs/heads/main.zip`.
6. Проверьте, что ассистент пересказал вам состояние, правила и список решений, прежде чем он начнёт что-то менять.

Я не знаю, какие инструменты есть у вашего ChatGPT (оболочка, запуск кода, коммиты в GitHub, браузер). Это влияет на проверки: тесты RevEng и Social рассчитаны на Linux с оболочкой, Forge проверяется на настоящем Windows через GitHub Actions. Если коммитить в GitHub ChatGPT не может, правки придётся вносить вам или другим инструментом.

## Ветки репозитория (на момент снимка)

| Ветка | Для чего |
| --- | --- |
| `main` | рабочая ветка всех проектов |
| `results` | вывод первого живого прогона движка RevEng (`reveng/runs/…`) |
| `forge-last-green` | страховочная копия последнего зелёного состояния Forge (обновляется CI) |
| `forge-ci-results` | результаты проверок Forge на Windows (JSON, скриншоты, журналы) |
| `forge/055-research-draft`, `forge/ci-windows` | старые рабочие ветки Forge |
| `social/v1` | ветка Social (влита в `main`) |
| `social-results` | готовые Reels, индекс, отозванные результаты |

## Что не переносится само

- Документы проекта «RevEng» в claude.ai (`claude/…`): их копии уже лежат в `reveng/` и здесь.
- Память и контекст сессий Claude: всё важное записано в файлах этой папки и в `docs/` проектов.
- Данные в Supabase, секреты GitHub Actions, локальные файлы и папки на вашем компьютере. Мне они недоступны (компьютер к сессии не был подключён), поэтому ничего из этого не пересказано и не проверено.
- Большие двоичные файлы остаются на своих местах: релизные ZIP Forge в `forge/releases/` и `forge/archive/`, видео Social в ветке `social-results`.

## Честные оговорки

- Я работал только над **RevEng** (эта сессия). По **Forge** и **Social** я прочитал их документы в репозитории и сделал вводные по ним; сами проекты я не запускал и не проверял. Всё, что там сказано о состоянии, взято из их `docs/`.
- Я не открывал файлы workflow, `config.json` Social и код: чтение отказало по правилам безопасности среды, а для вводной это не требовалось.
- В `social/docs/CURRENT_STATE.md` счётчики (2 принятых Reels) устарели: `OWNER_REVIEW.md` и `WORKLOG.md` говорят о 5 принятых. Верить последним.
- Правило владельца «не трогать `forge/` из сессий RevEng» соблюдено: из `forge/` и `social/` я только читал.
