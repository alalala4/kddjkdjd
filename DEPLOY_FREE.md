# Бесплатный деплой бота

Три лучших бесплатных варианта. Рекомендую **Railway** - проще всего.

---

## Вариант 1: Railway (рекомендую)

Бесплатно: $5 кредитов каждый месяц (хватает на бота 24/7).

### Шаги:

1. Зарегистрируйтесь на https://railway.app (через GitHub)
2. Нажмите "New Project" -> "Deploy from GitHub Repo"
3. Подключите репозиторий с ботом (или загрузите файлы вручную через "Empty Project" -> "Add Service")
4. В настройках сервиса добавьте переменные окружения (Variables):
   ```
   TELEGRAM_TOKEN=ваш_токен
   OPENAI_API_KEY=ваш_ключ
   ALLOWED_USER_ID=ваш_id
   # если ключ от OpenAI-совместимого провайдера:
   OPENAI_BASE_URL=https://api.example.com/v1
   CHAT_MODEL=название_модели_у_провайдера
   ENABLE_WEB_SEARCH=0
   ENABLE_IMAGE_GENERATION=0
   ```
5. Railway автоматически определит Python. В репозитории уже есть `railway.json` со стартовой командой `python bot.py`.

### Плюсы:
- Реально бесплатно (5$/мес кредитов хватает)
- Автоматический деплой при пуше в GitHub
- Логи в реальном времени
- Не засыпает (в отличие от Render)

### Минусы:
- Нужна карта для верификации (деньги не списывают)
- Если бот жрёт много RAM (маловероятно) - может выйти за лимит

---

## Вариант 2: Render

Бесплатно: Free tier для Background Workers.

### Шаги:

1. Зарегистрируйтесь на https://render.com
2. New -> Background Worker
3. Подключите GitHub-репо или загрузите код
4. Runtime: Python 3
5. Build command: `pip install -r requirements.txt`
6. Start command: `python bot.py`
7. Добавьте переменные окружения (Environment)

### Плюсы:
- Полностью бесплатно
- Простая настройка

### Минусы:
- На бесплатном тарифе **засыпает через 15 минут без активности** (для web services, но Background Worker должен работать)
- Холодный старт 30-50 секунд после сна
- Медленнее Railway

---

## Вариант 3: Oracle Cloud Free Tier (VPS навсегда)

Бесплатно: полноценный VPS (1 CPU, 1 GB RAM) **навсегда**, без срока.

### Шаги:

1. Зарегистрируйтесь на https://cloud.oracle.com (нужна карта, не списывают)
2. Создайте Compute Instance:
   - Shape: VM.Standard.E2.1.Micro (Always Free)
   - OS: Ubuntu 22.04
   - Скачайте SSH-ключ
3. Подключитесь по SSH:
   ```bash
   ssh -i ваш_ключ.pem ubuntu@ip_адрес
   ```
4. Установите Python и зависимости:
   ```bash
   sudo apt update && sudo apt install python3-pip -y
   git clone ваш_репо
   cd telegram-bot
   pip3 install -r requirements.txt
   ```
5. Создайте файл `.env`:
   ```bash
   nano .env
   # Заполните ключи
   ```
6. Запустите как сервис:
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
   User=ubuntu
   WorkingDirectory=/home/ubuntu/telegram-bot
   EnvironmentFile=/home/ubuntu/telegram-bot/.env
   ExecStart=/usr/bin/python3 /home/ubuntu/telegram-bot/bot.py
   Restart=always
   RestartSec=10

   [Install]
   WantedBy=multi-user.target
   ```
   ```bash
   sudo systemctl daemon-reload
   sudo systemctl enable ai-bot
   sudo systemctl start ai-bot
   ```

### Плюсы:
- Полноценный VPS навсегда бесплатно
- Не засыпает, не перезапускается
- Полный контроль
- Можно добавить другие боты/сервисы

### Минусы:
- Сложнее настроить (нужен SSH, базовые навыки Linux)
- Регистрация иногда отклоняет аккаунты (попробуйте с другой карты)

---

## Что выбрать

| Ваш уровень | Рекомендация |
|---|---|
| Совсем новичок | **Railway** - три клика и работает |
| Немного разбираюсь | **Render** - бесплатно и просто |
| Знаю Linux / хочу надёжно | **Oracle Cloud** - навсегда бесплатный VPS |

---

## Важно про API-ключи

Бесплатный сервер - это только хостинг. Стоимость API зависит от выбранного провайдера:

- **OpenAI** - оплачивается по тарифам OpenAI.
- **OpenAI-совместимые провайдеры** - укажите их `OPENAI_BASE_URL`, `CHAT_MODEL` и отключите функции, которые провайдер не поддерживает.

---

## Procfile (для Railway и Render)

Создайте файл `Procfile` в корне проекта:

```
worker: python bot.py
```

## runtime.txt (опционально)

Если платформа просит указать версию Python:

```
python-3.11.7
```
