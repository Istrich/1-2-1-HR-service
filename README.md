# HR 1-2-1 Web — Веб-версия бота для аналитики интервью

Локальное веб-приложение для обработки аудиозаписей 1-2-1 интервью:
транскрипция (OpenAI Whisper) → аналитический HR-отчёт (GPT) → Word-документ (.docx).

## Возможности

- Загрузка аудио/видео-файлов или обработка по ссылке (Google Drive, Dropbox)
- Транскрипция с таймкодами: локально **openai-whisper** (по умолчанию, см. `WHISPER_MODEL` в `.env`) или через API OpenAI (`WHISPER_BACKEND=api`)
- Интерфейс workspace: плеер, транскрипт с сегментами, отчёт, доработка отчёта по комментарию, экспорт в Word
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

## Конфигурация (.env)

| Переменная | Описание | Обязательно |
|---|---|---|
| `OPENAI_API_KEY` | API-ключ OpenAI | Да |
| `USERS` | Пользователи (формат `user:pass,user2:pass2`) | Да |
| `SECRET_KEY` | Ключ для JWT-токенов (генерируется автоматически) | Нет |
| `JWT_EXPIRE_HOURS` | Время жизни токена авторизации (по умолч. 24ч) | Нет |

## Структура проекта

```
hr121-web/
├── app.py               # FastAPI-сервер (основная логика)
├── static/
│   └── index.html       # React SPA (фронтенд)
├── outputs/             # Сгенерированные файлы (транскрипции, отчёты)
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
