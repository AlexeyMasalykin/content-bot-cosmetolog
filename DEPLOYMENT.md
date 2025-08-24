# 🚀 Инструкция по деплою Content Bot

## 📋 Предварительные требования

1. **Docker** - установлен и запущен
2. **Git** - для клонирования репозитория
3. **Права root** - для настройки systemd сервиса

## 🔧 Подготовка к деплою

### 1. Клонирование проекта
```bash
git clone <your-repo-url>
cd content_bot_new
```

### 2. Настройка переменных окружения
Создайте файл `.env` с необходимыми переменными:

```bash
cp .env.example .env
nano .env
```

**Обязательные переменные:**
```env
# Telegram Bot
TELEGRAM_BOT_TOKEN=your_bot_token_here
TELEGRAM_CHANNEL_ID=-1001234567890
ADMIN_CHAT_ID=123456789

# OpenAI
OPENAI_API_KEY=sk-your-openai-key-here
OPENAI_MODEL_TEXT=gpt-4o
OPENAI_MODEL_PROMPT=gpt-4o

# VK API
VK_ACCESS_TOKEN=your_vk_token_here
VK_GROUP_ID=231774659

# Yandex Cloud (для генерации изображений)
YC_FOLDER_ID=your_folder_id
YC_IAM_TOKEN=your_iam_token
```

## 🚀 Деплой

### Вариант 1: Автоматический деплой (рекомендуется)
```bash
./deploy.sh
```

### Вариант 2: Ручной деплой
```bash
# Сборка образа
docker build -t content-bot:latest .

# Создание volume для данных
docker volume create content-bot-data

# Запуск контейнера
docker run -d \
    --name content-bot \
    --restart unless-stopped \
    --env-file .env \
    -v content-bot-data:/app/data \
    content-bot:latest
```

## ⚙️ Настройка автозапуска

### 1. Установка systemd сервиса
```bash
sudo ./setup-service.sh
```

### 2. Запуск сервиса
```bash
sudo systemctl start content-bot
sudo systemctl status content-bot
```

## 📊 Мониторинг и управление

### Просмотр логов
```bash
# Логи контейнера
docker logs content-bot
docker logs -f content-bot  # в реальном времени

# Логи systemd сервиса
sudo journalctl -u content-bot -f
```

### Управление ботом
```bash
# Docker команды
docker stop content-bot
docker start content-bot
docker restart content-bot

# Systemd команды
sudo systemctl stop content-bot
sudo systemctl start content-bot
sudo systemctl restart content-bot
```

### Обновление и перезапуск бота

#### Быстрый перезапуск (без изменений кода)
```bash
# Перезапуск через systemd
sudo systemctl restart content-bot

# Проверка статуса
sudo systemctl status content-bot
```

#### Обновление с изменениями кода
```bash
# 1. Остановка бота
sudo systemctl stop content-bot

# 2. Получение обновлений (если используется Git)
git pull

# 3. Обновление зависимостей (если изменился requirements)
source venv/bin/activate
pip install -r requirements_deploy.txt

# 4. Запуск бота
sudo systemctl start content-bot

# 5. Проверка логов
sudo journalctl -u content-bot -f
```

#### Обновление .env файла
```bash
# 1. Редактирование .env
nano .env

# 2. Перезапуск для применения изменений
sudo systemctl restart content-bot
```

#### Docker обновление (если используется)
```bash
# Остановка
docker stop content-bot
docker rm content-bot

# Получение обновлений
git pull

# Пересборка и запуск
./deploy.sh
```

## 🔒 Безопасность

1. **Файл .env** - не добавляйте в Git, содержит секретные ключи
2. **Права доступа** - ограничьте доступ к директории проекта
3. **Обновления** - регулярно обновляйте зависимости
4. **Мониторинг** - следите за логами на предмет ошибок

## 🔧 Администрирование бота

### Управление состоянием бота
```bash
# Просмотр состояния бота
cat bot_state.json | python3 -m json.tool

# Бэкап состояния
cp bot_state.json bot_state_backup_$(date +%Y%m%d_%H%M%S).json

# Очистка состояния (ОСТОРОЖНО!)
echo '{}' > bot_state.json
sudo systemctl restart content-bot
```

### Мониторинг ресурсов
```bash
# Использование памяти и CPU ботом
ps aux | grep "python.*bot.py"

# Размер лог-файлов
sudo du -sh /var/log/journal/

# Очистка старых логов (старше 7 дней)
sudo journalctl --vacuum-time=7d
```

### Настройка администратора
После деплоя обязательно:
1. Откройте бота в Telegram
2. Напишите команду `/admin` - вы станете администратором
3. Используйте `/start_scheduler` для запуска автоматического планирования

### Изменение токенов и ключей
```bash
# 1. Остановка бота
sudo systemctl stop content-bot

# 2. Редактирование .env
nano .env

# 3. Проверка синтаксиса .env (опционально)
cat .env | grep -v "^#" | grep -v "^$"

# 4. Перезапуск
sudo systemctl start content-bot

# 5. Проверка успешного запуска
sudo systemctl status content-bot
```

## 🐛 Решение проблем

### Бот не отвечает
```bash
# Проверка статуса
docker ps -a | grep content-bot
sudo systemctl status content-bot

# Проверка логов
docker logs content-bot
```

### Ошибки API
- Проверьте корректность токенов в `.env`
- Убедитесь, что у бота есть права в канале/группе
- Проверьте лимиты API (OpenAI, VK)

### Проблемы с изображениями
- Проверьте настройки Yandex Cloud
- Убедитесь, что IAM токен актуален
- Проверьте права доступа к Yandex Vision

## 📈 Масштабирование

### Для высоких нагрузок
1. Используйте webhook вместо polling
2. Настройте балансировщик нагрузки
3. Вынесите базу данных в отдельный контейнер
4. Используйте Redis для кэширования

## 🎯 Полезные команды

```bash
# Полная очистка (ОСТОРОЖНО!)
docker stop content-bot
docker rm content-bot
docker rmi content-bot:latest
docker volume rm content-bot-data

# Бэкап данных
docker cp content-bot:/app/data ./backup/

# Восстановление данных
docker cp ./backup/ content-bot:/app/data/
```

---

**🎉 Готово! Ваш Content Bot успешно развернут и готов к работе!**
