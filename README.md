# HR 1-2-1 Web — Веб-версия бота для аналитики интервью

Локальное веб-приложение для обработки аудиозаписей 1-2-1 интервью:
транскрипция (OpenAI Whisper) → аналитический HR-отчёт (GPT) → Word-документ (.docx).

## Возможности

- Загрузка аудио/видео-файлов или обработка по ссылке (Google Drive, Dropbox)
- Транскрипция с таймкодами: локально **openai-whisper** (по умолчанию, см. `WHISPER_MODEL` в `.env`) или через API OpenAI (`WHISPER_BACKEND=api`)
- Интерфейс workspace: плеер, транскрипт с сегментами, отчёт, доработка отчёта по комментарию, экспорт в Word; вкладка «История» — сохранённые отчёты (поиск, переименование, удаление, повторное открытие)
- Генерация структурированного HR-отчёта через GPT
- Формирование Word-документа (.docx) по кнопке экспорта
- Генерация письма с фиксацией договорённостей
- Настройка промтов (модальное окно в шапке)
- Авторизация с поддержкой нескольких пользователей
- Адаптивная вёрстка

## Быстрый старт на Mac Mini

### 1. Установка зависимостей

```bash
# Homebrew (если нет)
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Python 3.11+ и ffmpeg
brew install python@3.12 ffmpeg
```

### 2. Клонирование и настройка

```bash
# Перейти в директорию проекта
cd ~/hr121-web

# Создать виртуальное окружение
python3 -m venv venv
source venv/bin/activate

# Установить зависимости
pip install -r requirements.txt

# Скопировать и настроить конфиг
cp .env.example .env
nano .env  # вписать OPENAI_API_KEY и пользователей
```

### 3. Запуск

```bash
source venv/bin/activate
python app.py
```

Приложение будет доступно по адресу: **http://localhost:8080**

Для доступа с других устройств в сети: **http://<IP-мак-мини>:8080**

### 4. Автозапуск (launchd)

Чтобы приложение запускалось автоматически при старте Mac Mini:

```bash
cat > ~/Library/LaunchAgents/com.hr121.web.plist << 'EOF'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.hr121.web</string>
    <key>ProgramArguments</key>
    <array>
        <string>/Users/YOUR_USERNAME/hr121-web/venv/bin/python</string>
        <string>/Users/YOUR_USERNAME/hr121-web/app.py</string>
    </array>
    <key>WorkingDirectory</key>
    <string>/Users/YOUR_USERNAME/hr121-web</string>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>/Users/YOUR_USERNAME/hr121-web/logs/stdout.log</string>
    <key>StandardErrorPath</key>
    <string>/Users/YOUR_USERNAME/hr121-web/logs/stderr.log</string>
</dict>
</plist>
EOF

# Заменить YOUR_USERNAME на реальное имя пользователя
sed -i '' "s/YOUR_USERNAME/$(whoami)/g" ~/Library/LaunchAgents/com.hr121.web.plist

# Создать папку для логов
mkdir -p ~/hr121-web/logs

# Включить автозапуск
launchctl load ~/Library/LaunchAgents/com.hr121.web.plist
```

Управление:
```bash
# Остановить
launchctl unload ~/Library/LaunchAgents/com.hr121.web.plist

# Запустить
launchctl load ~/Library/LaunchAgents/com.hr121.web.plist
```

### 5. Docker: образ, данные вне контейнера, автозапуск

Нужны [Docker Desktop для Mac](https://www.docker.com/products/docker-desktop/) (или Colima с `docker compose`). Отчёты, каталог истории, ключи из UI и кэш весов **локального** Whisper хранятся в каталоге на Mac, а не в слое образа: при `docker compose build` и пересоздании контейнера они не пропадают.

**Каталог данных** задаётся переменной `HR121_DATA_DIR` (по умолчанию `./data` рядом с `docker-compose.yml`):

| Путь на хосте | Назначение |
|---------------|------------|
| `$HR121_DATA_DIR/.env` | Секреты и настройки (тот же формат, что `.env.example`) |
| `$HR121_DATA_DIR/outputs/` | Аудио, транскрипты, отчёты, `reports_catalog.json` |
| `$HR121_DATA_DIR/cache/` | Кэш Whisper (`XDG_CACHE_HOME`), чтобы не качать `.pt` заново |

Первый запуск:

```bash
cd /path/to/hr121-web
./scripts/init-docker-data.sh    # создаёт data/.env из .env.example и каталоги
# отредактируйте data/.env
docker compose up -d --build
```

Приложение: **http://localhost:8080**. Остановка: `docker compose down` (данные на диске остаются).

Чтобы **при входе в систему** поднимался контейнер (после старта Docker), включите в Docker Desktop опцию вроде *Start Docker Desktop when you log in*, затем установите LaunchAgent:

```bash
REPO="$HOME/hr121-web"   # путь к клону
cp "$REPO/deploy/macos/com.hr121.docker.plist.example" ~/Library/LaunchAgents/com.hr121.docker.plist
sed -i '' "s|/ABSOLUTE/PATH/TO/hr121-web|$REPO|g" ~/Library/LaunchAgents/com.hr121.docker.plist
launchctl load ~/Library/LaunchAgents/com.hr121.docker.plist
```

Скрипт `scripts/docker-start-on-login.sh` ждёт доступности демона Docker и выполняет `docker compose up -d`. Логи: `logs/docker-launchd.log` и `logs/docker-launchd.err.log`.

Постоянный каталог вне репозитория (например `~/Library/Application Support/hr121-web`):

```bash
export HR121_DATA_DIR="$HOME/Library/Application Support/hr121-web"
mkdir -p "$HR121_DATA_DIR"
./scripts/init-docker-data.sh
HR121_DATA_DIR="$HR121_DATA_DIR" docker compose up -d --build
```

Если раньше использовали `.env` в корне репозитория, скопируйте его: `cp .env "$HR121_DATA_DIR/.env"`.

## Конфигурация (.env)

| Переменная | Описание | Обязательно |
|---|---|---|
| `OPENAI_API_KEY` | API-ключ OpenAI | Да |
| `USERS` | Пользователи (формат `user:pass,user2:pass2`) | Да |
| `SECRET_KEY` | Ключ для JWT-токенов (генерируется автоматически) | Нет |
| `JWT_EXPIRE_HOURS` | Время жизни токена авторизации (по умолч. 24ч) | Нет |

## Windows Desktop (.exe)

Текущий веб-режим не меняется: `python app.py` работает как раньше.  
Desktop-режим — это отдельная обёртка над тем же приложением.

### 0) Установка системных зависимостей (опционально, через bat)

```powershell
.\bootstrap_windows_env.bat
```

Скрипт пытается установить:
- Python 3.11 (`winget`, пакет `Python.Python.3.11`)
- ffmpeg (`winget`, пакет `Gyan.FFmpeg`, fallback `BtbN.FFmpeg.GPL`)

Если PATH обновился не сразу — закройте терминал и откройте новый.

### 1) Подготовка окружения на Windows

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements-desktop.txt
```

### 2) Локальный запуск в desktop-окне

```powershell
python desktop_main.py
```

### 3) Сборка `.exe` (PyInstaller, onedir)

```powershell
pyinstaller --noconfirm --windowed --onedir --name HR121Desktop `
  --add-data "static;static" `
  --add-data "outputs;outputs" `
  desktop_main.py
```

Готовый исполняемый файл: `dist\HR121Desktop\HR121Desktop.exe`.

Или одной командой через bat-скрипт из корня проекта:

```powershell
.\build_windows_exe.bat
```

Запуск собранного desktop-приложения:

```powershell
.\run_windows_desktop.bat
```

Примечания:
- `onedir` выбран специально для надёжной работы со `static/` и `outputs/`.
- Если окно не открывается на некоторых системах, установите [Microsoft Edge WebView2 Runtime](https://developer.microsoft.com/microsoft-edge/webview2/).
- `.env` храните рядом с приложением/рабочей директорией, секреты не вшивайте в репозиторий.

## Структура проекта

```
hr121-web/
├── app.py               # FastAPI-сервер (основная логика)
├── Dockerfile           # образ приложения (данные — тома в compose)
├── docker-compose.yml   # тома: .env, outputs, кэш Whisper на хосте
├── static/
│   └── index.html       # React SPA (фронтенд)
├── outputs/             # при запуске без Docker; в Docker — каталог из HR121_DATA_DIR
├── data/                # каталог по умолчанию для Docker (в .gitignore)
├── scripts/             # init-docker-data.sh, docker-start-on-login.sh
├── deploy/macos/        # пример plist для автозапуска Docker-стека
├── docs/                # Воркфлоу, планы, шаблоны ТЗ
├── requirements.txt
├── .env                 # Конфиг (не коммитить!)
├── .env.example
├── context.md           # Контекст проекта (для агентов и команды)
├── AGENTS.md            # Роли агентов (кратко)
└── README.md
```

## Документация для разработки

- [context.md](context.md) — актуальный обзор стека, API и ограничений.
- [docs/WORKFLOW.md](docs/WORKFLOW.md) — этапы работы, роли, артефакты.
- [docs/plans/](docs/plans/) — архитектурные планы (`TEMPLATE.md` — шаблон).
- [docs/specs/](docs/specs/) — технические задания (`TEMPLATE.md` — шаблон).
