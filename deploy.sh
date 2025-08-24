#!/bin/bash

# Content Bot Deploy Script
set -e

echo "🚀 Деплой Content Bot"
echo "===================="

# Проверка наличия .env файла
if [ ! -f .env ]; then
    echo "❌ Файл .env не найден!"
    echo "Создайте файл .env с необходимыми переменными:"
    echo "TELEGRAM_BOT_TOKEN=your_token"
    echo "OPENAI_API_KEY=your_key"
    echo "VK_ACCESS_TOKEN=your_token"
    echo "И другие..."
    exit 1
fi

echo "✅ Файл .env найден"

# Проверка Docker
if ! command -v docker &> /dev/null; then
    echo "❌ Docker не установлен!"
    echo "Установите Docker и повторите попытку"
    exit 1
fi

echo "✅ Docker доступен"

# Остановка предыдущего контейнера (если есть)
echo "🔄 Остановка предыдущего контейнера..."
docker stop content-bot 2>/dev/null || true
docker rm content-bot 2>/dev/null || true

# Сборка образа
echo "🏗️  Сборка Docker образа..."
docker build -t content-bot:latest .

# Создание volume для состояния
echo "📁 Создание volume для данных..."
docker volume create content-bot-data 2>/dev/null || true

# Запуск контейнера
echo "🚀 Запуск контейнера..."
docker run -d \
    --name content-bot \
    --restart unless-stopped \
    --env-file .env \
    -v content-bot-data:/app/data \
    content-bot:latest

echo "✅ Content Bot успешно запущен!"
echo ""
echo "📋 Полезные команды:"
echo "docker logs content-bot          # Просмотр логов"
echo "docker logs -f content-bot       # Просмотр логов в реальном времени"
echo "docker stop content-bot          # Остановка бота"
echo "docker start content-bot         # Запуск бота"
echo "docker restart content-bot       # Перезапуск бота"
echo ""
echo "🎉 Деплой завершен!"
