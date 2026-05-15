# РЕЙТ AI Bot

Личный Telegram-бот с ChatGPT (GPT-4o) и Gemini (2.5 Pro).
Текстовый чат + генерация изображений через DALL-E 3.

## Что умеет

- Текстовый диалог с ChatGPT (GPT-4o)
- Текстовый диалог с Gemini 2.5 Pro
- Переключение между моделями на лету
- Генерация изображений через DALL-E 3
- Запоминает контекст (последние 20 сообщений)
- Доступ только для вашего Telegram ID

## Быстрый старт

### 1. Получите API-ключи

| Что нужно | Где получить |
|---|---|
| Telegram Bot Token | Напишите @BotFather в Telegram, команда /newbot |
| OpenAI API Key | https://platform.openai.com/api-keys |
| Google AI API Key | https://aistudio.google.com/apikey |
| Ваш Telegram ID | Напишите @userinfobot в Telegram |

### 2. Установите зависимости

```bash
pip install -r requirements.txt
```

### 3. Настройте переменные окружения

```bash
cp .env.example .env
# Откройте .env и заполните ваши ключи
```

Или экспортируйте напрямую:

```bash
export TELEGRAM_TOKEN="ваш_токен"
export OPENAI_API_KEY="ваш_ключ"
export GOOGLE_AI_API_KEY="ваш_ключ"
export ALLOWED_USER_ID="ваш_telegram_id"
```

### 4. Запустите

```bash
python bot.py
```

## Команды бота

| Команда | Что делает |
|---|---|
| /start | Приветствие и список команд |
| /gpt | Переключиться на ChatGPT (GPT-4o) |
| /gemini | Переключиться на Gemini 2.5 Pro |
| /img описание | Сгенерировать картинку через DALL-E 3 |
| /clear | Очистить историю диалога |
| /model | Показать текущую модель |

Просто пишите текст - бот ответит через текущую активную модель.

## Деплой на VPS

### Вариант 1: systemd (рекомендую)

```bash
sudo nano /etc/systemd/system/ai-bot.service
```

Содержимое:

```ini
[Unit]
Description=AI Telegram Bot
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/root/telegram-bot
EnvironmentFile=/root/telegram-bot/.env
ExecStart=/usr/bin/python3 /root/telegram-bot/bot.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Запуск:

```bash
sudo systemctl daemon-reload
sudo systemctl enable ai-bot
sudo systemctl start ai-bot
sudo systemctl status ai-bot
```

### Вариант 2: Docker

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY bot.py .
CMD ["python", "bot.py"]
```

```bash
docker build -t ai-bot .
docker run -d --env-file .env --name ai-bot --restart always ai-bot
```

### Вариант 3: screen (самый простой)

```bash
screen -S bot
python bot.py
# Ctrl+A, D - отключиться от сессии
# screen -r bot - вернуться
```

## Стоимость API

| Сервис | Примерная стоимость |
|---|---|
| OpenAI GPT-4o | ~$2.50 / 1M входных токенов, ~$10 / 1M выходных |
| OpenAI DALL-E 3 HD | ~$0.08 за картинку |
| Google Gemini 2.5 Pro | бесплатно до 50 запросов/день, потом ~$1.25-2.50 / 1M токенов |

При личном использовании (50-100 сообщений в день) выходит ~$5-15/месяц.

## Примечания

- Бот работает в режиме polling (не webhook) - проще для настройки
- Gemini 2.5 Pro имеет бесплатный лимит в AI Studio - для личного использования может хватить
- DALL-E 3 генерирует только через OpenAI (Gemini Imagen пока не доступен в API)
- История хранится в памяти - при перезапуске бота сбрасывается
