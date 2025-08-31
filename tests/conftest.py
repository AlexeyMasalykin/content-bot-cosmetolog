"""
Конфигурация pytest для Content Bot
"""

import os
import sys
import pytest

# Добавляем корневую директорию в путь для импорта модулей
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

@pytest.fixture(autouse=True)
def setup_test_environment():
    """Настройка тестового окружения"""
    # Устанавливаем тестовые переменные окружения
    test_env_vars = {
        'BOT_TOKEN': 'test_bot_token',
        'OPENAI_API_KEY': 'test_openai_key',
        'YANDEX_API_KEY': 'test_yandex_key',
        'YANDEX_FOLDER_ID': 'test_folder_id',
        'VK_ACCESS_TOKEN': 'test_vk_token',
        'VK_GROUP_ID': 'test_group_id',
        'TELEGRAM_CHANNEL_ID': 'test_channel_id',
        'OPENAI_MODEL_TEXT': 'gpt-3.5-turbo',
        'OPENAI_MODEL_PROMPT': 'gpt-3.5-turbo',
        'VK_API_VERSION': '5.131'
    }
    
    # Сохраняем оригинальные значения
    original_env = {}
    for key in test_env_vars:
        if key in os.environ:
            original_env[key] = os.environ[key]
    
    # Устанавливаем тестовые значения
    for key, value in test_env_vars.items():
        os.environ[key] = value
    
    yield
    
    # Восстанавливаем оригинальные значения
    for key in test_env_vars:
        if key in original_env:
            os.environ[key] = original_env[key]
        elif key in os.environ:
            del os.environ[key]
