#!/bin/bash

# Скрипт для настройки GitHub репозитория Content Bot Cosmetolog

echo "🚀 Настройка GitHub репозитория Content Bot Cosmetolog"
echo "=============================================="

# Запрос GitHub username
read -p "Введите ваше имя пользователя GitHub: " GITHUB_USERNAME

if [ -z "$GITHUB_USERNAME" ]; then
    echo "❌ Имя пользователя не может быть пустым"
    exit 1
fi

echo "✅ Используем GitHub username: $GITHUB_USERNAME"

# Замена placeholder'ов в файлах
echo "📝 Замена placeholder'ов в файлах..."

# Замена в README.md
sed -i "s/your-username/$GITHUB_USERNAME/g" README.md
sed -i "s/YOUR_USERNAME/$GITHUB_USERNAME/g" README.md

# Замена в CONTRIBUTING.md
sed -i "s/YOUR_USERNAME/$GITHUB_USERNAME/g" CONTRIBUTING.md

echo "✅ Placeholder'ы заменены"

# Создание .env файла из примера
if [ ! -f .env ]; then
    echo "📋 Создание .env файла из примера..."
    cp env.example .env
    echo "✅ Файл .env создан"
    echo "⚠️  Не забудьте отредактировать .env с вашими API ключами!"
else
    echo "ℹ️  Файл .env уже существует"
fi

# Проверка Git статуса
echo "📊 Статус Git репозитория:"
git status

echo ""
echo "🎉 Настройка завершена!"
echo ""
echo "📋 Следующие шаги:"
echo "1. Создайте репозиторий на GitHub: https://github.com/new"
echo "2. Назовите его 'content-bot-cosmetolog'"
echo "3. НЕ инициализируйте с README, .gitignore или лицензией"
echo "4. Выполните команды:"
echo "   git remote add origin https://github.com/$GITHUB_USERNAME/content-bot-cosmetolog.git"
echo "   git push -u origin main"
echo ""
echo "🔧 Не забудьте отредактировать .env файл с вашими API ключами!"
