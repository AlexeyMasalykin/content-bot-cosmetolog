#!/bin/bash

# Content Bot Service Setup Script
set -e

echo "🔧 Настройка systemd сервиса для Content Bot"
echo "============================================"

# Проверка прав root
if [ "$EUID" -ne 0 ]; then
    echo "❌ Запустите скрипт от имени root (sudo)"
    exit 1
fi

# Копирование service файла
echo "📁 Копирование service файла..."
cp content-bot.service /etc/systemd/system/

# Перезагрузка systemd
echo "🔄 Перезагрузка systemd..."
systemctl daemon-reload

# Включение автозапуска
echo "✅ Включение автозапуска..."
systemctl enable content-bot.service

echo "✅ Systemd сервис настроен!"
echo ""
echo "📋 Полезные команды:"
echo "sudo systemctl start content-bot     # Запуск сервиса"
echo "sudo systemctl stop content-bot      # Остановка сервиса"
echo "sudo systemctl restart content-bot   # Перезапуск сервиса"
echo "sudo systemctl status content-bot    # Статус сервиса"
echo "sudo systemctl disable content-bot   # Отключить автозапуск"
echo ""
echo "🎉 Настройка завершена!"
