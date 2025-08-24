# 🚀 Ручной деплой Content Bot

## Если возникают проблемы с терминалом или Docker

### 1️⃣ Создание .env файла

Создайте файл `.env` в корне проекта со следующим содержимым:

```env
# Telegram Bot
TELEGRAM_BOT_TOKEN=your_bot_token_from_botfather
TELEGRAM_CHANNEL_ID=-1001234567890
ADMIN_CHAT_ID=123456789

# OpenAI
OPENAI_API_KEY=sk-your-openai-api-key-here
OPENAI_MODEL_TEXT=gpt-4o
OPENAI_MODEL_PROMPT=gpt-4o

# VK API
VK_ACCESS_TOKEN=your_vk_access_token
VK_GROUP_ID=231774659

# Yandex Cloud
YC_FOLDER_ID=your_yandex_cloud_folder_id
YC_IAM_TOKEN=your_yandex_iam_token
```

### 2️⃣ Быстрый запуск

```bash
python3 quick-deploy.py
```

### 3️⃣ Альтернативный запуск

Если quick-deploy не работает:

```bash
# Активация виртуального окружения (если есть)
source venv/bin/activate

# Установка зависимостей
pip install -r requirements_deploy.txt

# Запуск бота
python3 bot.py
```

### 4️⃣ Проверка работы

После запуска бот должен:
- ✅ Подключиться к Telegram API
- ✅ Загрузить состояние из bot_state.json
- ✅ Запустить планировщик задач
- ✅ Отвечать на команды в Telegram

### 5️⃣ Автозапуск (systemd)

Создайте файл `/etc/systemd/system/content-bot.service`:

```ini
[Unit]
Description=Content Bot
After=network.target

[Service]
Type=simple
User=alex2061
WorkingDirectory=/root/content_bot_new
Environment=PATH=/root/content_bot_new/venv/bin
ExecStart=/root/content_bot_new/venv/bin/python /root/content_bot_new/bot.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Активация:
```bash
sudo systemctl daemon-reload
sudo systemctl enable content-bot
sudo systemctl start content-bot
```

### 6️⃣ Мониторинг

```bash
# Статус сервиса
sudo systemctl status content-bot

# Логи
sudo journalctl -u content-bot -f

# Остановка
sudo systemctl stop content-bot
```

---

**🎯 Главное: убедитесь, что файл .env содержит ваши реальные токены и ключи!**
