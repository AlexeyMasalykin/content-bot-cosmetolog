"""
Базовые тесты для Content Bot
"""

import sys
import os

# Добавляем корневую директорию в путь для импорта модулей
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_imports():
    """Тест импорта основных модулей"""
    try:
        import state
        import bot
        assert True, "Основные модули импортируются успешно"
    except ImportError as e:
        assert False, f"Ошибка импорта: {e}"


def test_config_structure():
    """Тест структуры конфигурации"""
    # Проверяем, что файл config.py существует и имеет правильную структуру
    import os
    config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config.py')
    assert os.path.exists(config_path), "Файл config.py должен существовать"
    
    # Читаем файл и проверяем наличие основных переменных
    with open(config_path, 'r', encoding='utf-8') as f:
        content = f.read()
        assert 'BOT_TOKEN' in content, "BOT_TOKEN должен быть определен в config.py"
        assert 'OPENAI_API_KEY' in content, "OPENAI_API_KEY должен быть определен в config.py"
        assert 'YANDEX_API_KEY' in content, "YANDEX_API_KEY должен быть определен в config.py"


def test_state_functions():
    """Тест функций управления состоянием"""
    import state
    
    # Проверяем, что функции существуют
    assert hasattr(state, 'save_state'), "Функция save_state должна существовать"
    assert hasattr(state, 'load_state'), "Функция load_state должна существовать"
    assert callable(state.save_state), "save_state должна быть функцией"
    assert callable(state.load_state), "load_state должна быть функцией"


def test_basic_math():
    """Простой тест математики для проверки pytest"""
    assert 2 + 2 == 4, "Базовая математика должна работать"
    assert 10 * 5 == 50, "Умножение должно работать"


if __name__ == "__main__":
    # Запуск тестов напрямую
    test_imports()
    test_config_structure()
    test_state_functions()
    test_basic_math()
    print("Все тесты прошли успешно!")
