import threading
from typing import Dict, Any
import json
import os
from datetime import datetime

# Существующие состояния для быстрых постов
user_drafts: Dict[int, Dict[str, Any]] = {}
user_states: Dict[int, str] = {}

# Новые состояния для планирования контента
scheduled_posts: Dict[str, Any] = {
    "pending_topics": None,  # Темы, ожидающие одобрения
    "approved_topics": [],  # Одобренные темы
    "pending_posts": [],  # Посты, ожидающие одобрения
    "approved_posts": [],  # Одобренные посты для публикации
    "published_posts": [],  # Архив опубликованных постов
}

# Состояния процесса планирования
planning_states: Dict[int, Dict[str, Any]] = {}

store_lock = threading.Lock()


# Путь к файлу для сохранения состояния
STATE_FILE = "bot_state.json"


def save_state():
    """Сохраняет состояние в файл"""
    try:
        state_data = {
            "scheduled_posts": scheduled_posts,
            "planning_states": planning_states,
            "timestamp": datetime.now().isoformat(),
        }
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(state_data, f, ensure_ascii=False, indent=2, default=str)
    except Exception as e:
        print(f"Error saving state: {e}")


def load_state():
    """Загружает состояние из файла"""
    global scheduled_posts, planning_states
    try:
        if os.path.exists(STATE_FILE):
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                state_data = json.load(f)
                scheduled_posts.clear()
                scheduled_posts.update(state_data.get("scheduled_posts", {}))
                planning_states.clear()
                planning_states.update(state_data.get("planning_states", {}))
                print("State loaded successfully")
    except Exception as e:
        print(f"Error loading state: {e}")
        # Инициализируем пустые состояния в случае ошибки
        scheduled_posts = {
            "pending_topics": None,
            "approved_topics": [],
            "pending_posts": [],
            "approved_posts": [],
            "published_posts": [],
        }
        planning_states = {}


# Автоматически загружаем состояние при импорте
load_state()
