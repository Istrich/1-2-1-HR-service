# HR 1-2-1 Web

Локальное веб-приложение для обработки аудиозаписей 1-2-1 интервью:

**транскрипция (Whisper)** → **HR-отчёт (GPT / DeepSeek)** → **доработка** → **экспорт .docx**

Репозиторий: [github.com/Istrich/1-2-1-HR-service](https://github.com/Istrich/1-2-1-HR-service)

## Возможности

- Загрузка аудио/видео или обработка по ссылке (Google Drive, Dropbox)
- Транскрипция с таймкодами: **локально** (`openai-whisper`) или через **OpenAI API** (`WHISPER_BACKEND=api`)
- Workspace: плеер, транскрипт, отчёт, доработка по комментарию, экспорт Word
- Вкладка «История»: поиск, переименование, удаление, повторное открытие отчётов
- Генерация письма с фиксацией договорённостей
- Настройка промтов и режимов ИИ в UI («ИИ и API»)
- **Живой прогресс обработки** — этапы с сервера (`GET /api/process/status`)
- Авторизация, несколько пользователей (JWT)

## Требования

| Компонент | Версия |
|-----------|--------|
| Python | 3.11+ |
| ffmpeg | в `PATH` (обязателен) |
| OpenAI API | для Whisper API и/или отчёта |
| DeepSeek API | опционально, если `REPORT_AI_PROVIDER=deepseek` |

Для локального Whisper (`WHISPER_BACKEND=local`) при первом запуске скачиваются веса модели; нужны RAM и место на диске (модель `small` — разумный компромисс).

---

## Быстрый старт (Windows)

### 1. Системные зависимости

```powershell
# Опционально: Python 3.11 и ffmpeg через winget
.\bootstrap_windows_env.bat
```

Или вручную: [Python 3.11+](https://www.python.org/downloads/), [ffmpeg](https://ffmpeg.org/download.html) в PATH.

### 2. Окружение и конфиг

```powershell
cd путь\к\1-2-1-HR-service
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

copy .env.example .env
# Отредактируйте .env: USERS, OPENAI_API_KEY (и при необходимости другие ключи)
```

### 3. Запуск

```powershell
.\.venv\Scripts\Activate.ps1
python app.py
```

Откройте **http://localhost:8080** (с других машин в сети: `http://<IP-хоста>:8080`).

Остановка: `Ctrl+C` в терминале.

---

## Быстрый старт (macOS / Linux)

```bash
brew install python@3.12 ffmpeg   # или аналог в дистрибутиве

cd 1-2-1-HR-service
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
# nano .env

python app.py
```

---

## Конфигурация (`.env`)

Скопируйте `.env.example` → `.env`. **Не коммитьте `.env`** — он в `.gitignore`.

| Переменная | Назначение | По умолчанию |
|------------|------------|--------------|
| `USERS` | Логины: `user:pass,user2:pass2` | — (обязательно) |
| `OPENAI_API_KEY` | OpenAI: Whisper API и/или отчёт | — |
| `DEEPSEEK_API_KEY` | DeepSeek для отчёта/письма | — |
| `REPORT_AI_PROVIDER` | `openai` \| `deepseek` | `openai` |
| `OPENAI_REPORT_MODEL` | Модель OpenAI для отчёта | `gpt-4o` |
| `DEEPSEEK_MODEL` | Модель DeepSeek | `deepseek-chat` |
| `WHISPER_BACKEND` | `local` \| `api` | `local` |
| `WHISPER_MODEL` | Модель локального Whisper (`tiny`…`medium`…) | `small` |
| `SECRET_KEY` | Подпись JWT | генерируется при старте |
| `JWT_EXPIRE_HOURS` | Срок жизни токена | `24` |

Ключи и режимы можно менять в UI без правки кода (сохраняются в `.env` на сервере).

### Режимы транскрипции

| Режим | Когда использовать |
|-------|---------------------|
| `WHISPER_BACKEND=api` | Быстрый старт, нет GPU/RAM; нужен `OPENAI_API_KEY`. Лимит **25 МБ на файл** — длинные записи нарезаются автоматически. |
| `WHISPER_BACKEND=local` | Без отправки аудио в облако; нужен `openai-whisper` и ffmpeg. |

### Ожидаемое время обработки

Зависит от длины записи и режима. Ориентир для записи ~30 мин при `WHISPER_BACKEND=api`:

- подготовка и нарезка: секунды;
- транскрипция (несколько частей): 5–15 мин;
- отчёт GPT: 3–10 мин.

На экране обработки отображается **реальный этап с сервера**, не таймер.

---

## Docker

Данные (`.env`, `outputs/`, кэш Whisper) хранятся на хосте в `HR121_DATA_DIR` (по умолчанию `./data`), а не в образе.

```bash
./scripts/init-docker-data.sh    # создаёт data/.env и каталоги
# отредактируйте data/.env
docker compose up -d --build
```

Приложение: **http://localhost:8080**. Остановка: `docker compose down` (данные на диске остаются).

Автозапуск на macOS: `deploy/macos/com.hr121.docker.plist.example`, скрипт `scripts/docker-start-on-login.sh`.

---

## Windows Desktop (окно вместо браузера)

Веб-режим (`python app.py`) не меняется. Desktop — обёртка `pywebview` над тем же сервером.

```powershell
pip install -r requirements-desktop.txt
python desktop_main.py
```

Сборка `.exe`: `.\build_windows_exe.bat` или см. `build_windows_exe.bat`.  
Нужен [WebView2 Runtime](https://developer.microsoft.com/microsoft-edge/webview2/) на целевой машине.

---

## API (кратко)

Префикс `/api`, защищённые маршруты — заголовок `Authorization: Bearer <jwt>`.

| Метод | Путь | Назначение |
|-------|------|------------|
| POST | `/api/login` | Вход |
| GET | `/api/me` | Текущий пользователь |
| POST | `/api/process/upload` | Загрузка файла → транскрипт + отчёт |
| POST | `/api/process/url` | Обработка по URL |
| GET | `/api/process/status` | Прогресс обработки (для UI) |
| GET | `/api/reports` | История отчётов |
| GET/PATCH/DELETE | `/api/reports/{id}` | Открыть / переименовать / удалить |
| POST | `/api/refine` | Доработка отчёта |
| POST | `/api/export/docx` | Экспорт в Word |
| POST | `/api/email` | Черновик письма |
| GET/POST | `/api/prompts` | Промты отчёта и письма |
| GET/POST | `/api/settings/runtime` | Режимы ИИ и ключи |

Статика: `/`, `/static/*`. Файлы `outputs/` — с поддержкой HTTP Range (перемотка в плеере).

---

## Структура проекта

```
1-2-1-HR-service/
├── app.py                 # FastAPI: API, пайплайн, промты
├── desktop_main.py        # Desktop-launcher (Windows)
├── static/index.html      # SPA (React 18, CDN)
├── requirements.txt
├── requirements-desktop.txt
├── Dockerfile
├── docker-compose.yml
├── scripts/               # Docker: init, автозапуск
├── deploy/macos/          # Пример LaunchAgent
├── outputs/               # Отчёты и аудио (в .gitignore)
├── .env.example
└── README.md
```

---

## Устранение неполадок

| Симптом | Что проверить |
|---------|----------------|
| Чёрный экран при открытии | Обновите страницу (Ctrl+F5); смотрите консоль браузера (ошибка JS). |
| Ошибка 413 от OpenAI | Фрагмент > 25 МБ — обновите код (автонарезка) или уменьшите битрейт исходника. |
| Долгая «обработка» | Смотрите этап на экране и логи сервера; для длинных MP3 первая транскрипция через API — это нормально. |
| Двойной диалог выбора файла | Исправлено в актуальной версии `static/index.html`. |
| `ffmpeg` не найден | Установите ffmpeg и добавьте в PATH. |
| Кириллица в имени файла (Windows) | Сервер копирует файл в `source.mp3` — должно работать в актуальной версии. |

Логи сервера пишутся в stdout (терминал, где запущен `python app.py`).

---

## Лицензия и секреты

- Не коммитьте `.env`, `outputs/`, `.venv/`.
- В репозитории только код приложения и пользовательская документация (этот README).
