#!/usr/bin/env python3
"""
Quick Deploy Script для Content Bot
Запускает бот напрямую без Docker если есть проблемы с терминалом
"""

import os
import sys
import subprocess
import time

def log(message):
    print(f"[DEPLOY] {message}")

def check_env_file():
    """Проверка наличия .env файла"""
    if not os.path.exists('.env'):
        log("❌ Файл .env не найден!")
        log("Создайте файл .env со следующими переменными:")
        print("""
# Скопируйте и заполните своими значениями:
TELEGRAM_BOT_TOKEN=your_bot_token_from_botfather
TELEGRAM_CHANNEL_ID=-1001234567890
ADMIN_CHAT_ID=123456789
OPENAI_API_KEY=sk-your-openai-api-key-here
OPENAI_MODEL_TEXT=gpt-4o
OPENAI_MODEL_PROMPT=gpt-4o
VK_ACCESS_TOKEN=your_vk_access_token
VK_GROUP_ID=231774659
YC_FOLDER_ID=your_yandex_cloud_folder_id
YC_IAM_TOKEN=your_yandex_iam_token
        """)
        return False
    log("✅ Файл .env найден")
    return True

def install_requirements():
    """Установка зависимостей"""
    log("📦 Установка зависимостей...")
    try:
        subprocess.run([sys.executable, '-m', 'pip', 'install', '-r', 'requirements_deploy.txt'], 
                      check=True, capture_output=True)
        log("✅ Зависимости установлены")
        return True
    except subprocess.CalledProcessError as e:
        log(f"❌ Ошибка установки зависимостей: {e}")
        return False

def start_bot():
    """Запуск бота"""
    log("🚀 Запуск Content Bot...")
    try:
        # Запускаем бота
        subprocess.run([sys.executable, 'bot.py'], check=True)
    except subprocess.CalledProcessError as e:
        log(f"❌ Ошибка запуска бота: {e}")
        return False
    except KeyboardInterrupt:
        log("🛑 Бот остановлен пользователем")
        return True

def main():
    log("🎉 Content Bot Quick Deploy")
    log("=" * 40)
    
    # Проверяем .env файл
    if not check_env_file():
        return 1
    
    # Устанавливаем зависимости
    if not install_requirements():
        return 1
    
    # Запускаем бота
    log("Запуск бота... (Ctrl+C для остановки)")
    start_bot()
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
