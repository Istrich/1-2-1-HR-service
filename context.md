# Контекст проекта HR 1-2-1 Web

Живой снимок для агентов и разработчиков. После существенных изменений кода, API или деплоя — обновить этот файл.

## Назначение

Локальное веб-приложение для обработки записей 1-2-1 интервью: транскрипция (локальный Whisper или API) → аналитический HR-отчёт и черновик письма (GPT) → доработка отчёта, выгрузка `.docx`. Целевой сценарий — Mac Mini в локальной сети (см. `README.md`).

## Стек и точки входа

| Компонент | Технология |
|-----------|------------|
| Backend | Python 3.11+ (в README указан и 3.12), **FastAPI**, `uvicorn` |
| Frontend | Один файл **`static/index.html`**: React 18 с CDN, Babel in-browser; UI v2 — workspace (транскрипт + отчёт, плеер с промоткой по дорожке, независимая прокрутка панелей, режим «Редактировать» для отчёта, доработка отчёта через ИИ с транскриптом на сервере, экспорт DOCX) |
| AI | Транскрипция: **локально** `openai-whisper` (модель `WHISPER_MODEL`, по умолчанию `small`) или через API `whisper-1` при `WHISPER_BACKEND=api`. Отчёт/письмо: OpenAI Responses API (`gpt-4o`) |
| Документы | `python-docx` |
| Аудио | `ffmpeg` (обязателен в PATH) |
| HTTP-клиент | `aiohttp` — загрузка по URL |
| Auth | JWT (`PyJWT`), секрет из `SECRET_KEY` |

Запуск: `python app.py` → **http://0.0.0.0:8080** (доступ с других машин по IP хоста).

Desktop-режим (Windows): `desktop_main.py` поднимает тот же FastAPI локально (`127.0.0.1:8080`) и открывает UI в окне `pywebview`; сборка в `.exe` через PyInstaller (см. `README.md`).

**Docker:** в корне `Dockerfile` и `docker-compose.yml`. Данные не в образе: на хост монтируются `$HR121_DATA_DIR/.env`, `.../outputs`, `.../cache` (кэш весов локального Whisper через `XDG_CACHE_HOME=/data/cache`). Первый запуск: `./scripts/init-docker-data.sh`, затем `docker compose up -d --build`. Автовход: `deploy/macos/com.hr121.docker.plist.example` + `scripts/docker-start-on-login.sh` (см. `README.md`).

## Структура репозитория

```
hr121-web/
├── app.py              # Вся серверная логика (API, промпты, пайплайн)
├── desktop_main.py     # Desktop launcher (pywebview) для Windows
├── static/index.html   # SPA: логин, загрузка, промпты, результаты
├── outputs/            # Сгенерированные файлы (gitignore): аудио для плеера, transcript.json, report.md, reports_catalog.json
├── requirements.txt
├── requirements-desktop.txt  # desktop-зависимости (pywebview)
├── .env                # не коммитить (см. .env.example)
├── context.md          # этот файл
├── docs/               # воркфлоу, планы, ТЗ
└── README.md
```

## Конфигурация (переменные окружения)

Имена без значений; секреты не вносить в репозиторий.

| Переменная | Назначение |
|------------|------------|
| `OPENAI_API_KEY` | Ключ OpenAI (нужен для Whisper API и/или отчёта через OpenAI) |
| `USERS` | `user:pass,user2:pass2` — базовая авторизация |
| `SECRET_KEY` | Подпись JWT; если не задан — генерируется при старте (сессии сбросятся при перезапуске) |
| `JWT_EXPIRE_HOURS` | Срок жизни токена (по умолчанию 24) |
| `WHISPER_BACKEND` | `local` (по умолчанию) или `api` — облачный Whisper OpenAI |
| `WHISPER_MODEL` | Для локального режима: `tiny` / `base` / `small` / `medium` / … (по умолчанию `small`, разумно для ~18GB RAM) |
| `REPORT_AI_PROVIDER` | `openai` или `deepseek` — провайдер для отчёта, доработки и письма |
| `DEEPSEEK_API_KEY` | Ключ DeepSeek (если выбран DeepSeek) |
| `OPENAI_REPORT_MODEL` | Модель OpenAI для chat completions (по умолчанию `gpt-4o`) |
| `DEEPSEEK_MODEL` | Модель DeepSeek (по умолчанию `deepseek-chat`) |

Ключи и режимы можно менять в UI («ИИ и API»): запись в `.env` на сервере.

Копирование: `cp .env.example .env`.

## API (обзор)

Префикс `/api`. Защищённые маршруты — заголовок `Authorization: Bearer <jwt>`.

| Метод | Путь | Назначение |
|-------|------|------------|
| POST | `/api/login` | Логин → `{ token, username }` |
| GET | `/api/me` | Текущий пользователь |
| GET/POST | `/api/prompts` | Чтение и сохранение промптов отчёта/письма |
| POST | `/api/prompts/reset` | Сброс промпта к значению по умолчанию |
| POST | `/api/process/upload` | Загрузка файла → JSON с `segments`, `report`, `audio_file` (workspace) |
| POST | `/api/process/url` | Обработка по ссылке (form `url`) |
| POST | `/api/refine` | Доработка отчёта по комментарию (тело: `comment`, `current_report`) |
| POST | `/api/export/docx` | Экспорт отчёта в Word (`report_text`) → `{ file }` |
| GET | `/api/reports` | Список сохранённых отчётов (`?q=` — поиск по названию) |
| GET | `/api/reports/{id}` | Загрузить отчёт в сессию + полный JSON (транскрипт, сегменты, отчёт, аудио URL) |
| PATCH | `/api/reports/{id}` | Переименовать (`title`) и/или сохранить текст отчёта (`report`) |
| DELETE | `/api/reports/{id}` | Удалить запись каталога и файлы (аудио, транскрипт, отчёт, docx при наличии) |
| POST | `/api/email` | Письмо по транскрипции текущей сессии пользователя |
| GET | `/api/settings/runtime` | Текущие режимы ИИ/транскрипции, `openai_report_model`, флаги «ключ задан» |
| POST | `/api/settings/runtime` | Сохранение в `.env`: провайдер, Whisper, `openai_report_model`, опционально ключи |
| GET | `/api/settings/openai-report-models` | Модели OpenAI для отчёта: при `OPENAI_API_KEY` — живой список с `GET https://api.openai.com/v1/models`, иначе пресет в коде; ответ: `source`: `live` \| `preset`, опционально `hint` |
| GET | `/api/settings/whisper-local-models` | Список имён `openai-whisper` и проверка скачанных `.pt` в кэше (`~/.cache/whisper` или `XDG_CACHE_HOME/whisper`) |

Статика: `/static/*`. Файлы из `outputs/` отдаются маршрутом приложения с **поддержкой HTTP Range** (нужно для перемотки в `<audio>`); не через «голый» `StaticFiles` для `/outputs`.

## Поведение и ограничения

- Промпты по умолчанию и пользовательские — в коде и в памяти (`user_prompts`); перезапуск сбрасывает кастомные промпты.
- Данные сессии обработки (транскрипт, сегменты, отчёт) для письма и доработки — в памяти (`user_sessions`) по пользователю; перезапуск сервера сбрасывает сессию, но **каждый обработанный файл** сохраняется в `outputs/`: `{id}_audio.mp3`, `{id}_transcript.json`, `{id}_report.md`, индекс `outputs/reports_catalog.json` (по пользователю). Из UI вкладка «История»: поиск, переименование, удаление, повторное открытие.
- Загрузка файла ограничена `MAX_UPLOAD_MB` (в коде).
- Обработка аудио: конвертация в mono mp3, нарезка чанками, склейка транскрипции с приблизительными таймкодами по чанкам.
- CORS в коде: `allow_origins=["*"]` — при выводе в прод сужать при необходимости.

## Интеграции

- **OpenAI**: биллинг и лимиты — на стороне аккаунта; в коде не логировать ключи и полные тексты персональных данных без необходимости.
- **Google Drive / Dropbox**: нормализация ссылок в `normalize_url`; реальная загрузка зависит от доступности прямой ссылки на файл.

## Тестирование

Отдельный каталог `tests/` и зависимость `pytest` могут быть добавлены по мере внедрения; команда проверки: `pytest` (когда настроено).

## Связанные документы

- `docs/WORKFLOW.md` — роли агентов и этапы работы.
- `docs/plans/` — архитектурные планы по датам.
- `docs/specs/` — технические задания по фичам.
