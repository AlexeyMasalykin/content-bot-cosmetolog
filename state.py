import threading
from typing import Dict, Any
import json
import os
import base64
import uuid
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
TEMP_IMAGES_DIR = "temp_images"


def save_image_to_file(image_bytes):
    """Сохраняет изображение в файл и возвращает имя файла"""
    if not image_bytes:
        return None
    
    # Создаем папку если её нет
    os.makedirs(TEMP_IMAGES_DIR, exist_ok=True)
    
    # Генерируем уникальное имя файла
    filename = f"{uuid.uuid4().hex}.jpg"
    filepath = os.path.join(TEMP_IMAGES_DIR, filename)
    
    try:
        # Если image_bytes это base64 строка, декодируем её
        if isinstance(image_bytes, str):
            image_data = base64.b64decode(image_bytes)
        else:
            image_data = image_bytes
            
        with open(filepath, 'wb') as f:
            f.write(image_data)
        return filename
    except Exception as e:
        print(f"Error saving image to file: {e}")
        return None


def load_image_from_file(filename):
    """Загружает изображение из файла"""
    if not filename:
        return None
        
    filepath = os.path.join(TEMP_IMAGES_DIR, filename)
    try:
        if os.path.exists(filepath):
            with open(filepath, 'rb') as f:
                return f.read()
        else:
            print(f"Image file not found: {filepath}")
            return None
    except Exception as e:
        print(f"Error loading image from file: {e}")
        return None


def delete_image_file(filename):
    """Удаляет файл изображения"""
    if not filename:
        return
        
    filepath = os.path.join(TEMP_IMAGES_DIR, filename)
    try:
        if os.path.exists(filepath):
            os.remove(filepath)
            print(f"Image file deleted: {filename}")
    except Exception as e:
        print(f"Error deleting image file: {e}")


def json_serializer(obj):
    """Кастомный сериализатор для JSON, который правильно обрабатывает bytes"""
    if isinstance(obj, bytes):
        try:
            return base64.b64encode(obj).decode("utf-8")
        except Exception as e:
            print(f"Error encoding bytes to base64: {e}")
            return None
    elif hasattr(obj, '__dict__'):
        return obj.__dict__
    else:
        return str(obj)


def clean_data_for_json(data):
    """Очищает данные от несериализуемых объектов"""
    if isinstance(data, dict):
        cleaned = {}
        for key, value in data.items():
            try:
                # Проверяем, можно ли сериализовать значение
                json.dumps(value, default=json_serializer)
                cleaned[key] = clean_data_for_json(value)
            except (TypeError, ValueError):
                print(f"Warning: Removing non-serializable key '{key}' with value type {type(value)}")
                continue
        return cleaned
    elif isinstance(data, list):
        cleaned = []
        for item in data:
            try:
                json.dumps(item, default=json_serializer)
                cleaned.append(clean_data_for_json(item))
            except (TypeError, ValueError):
                print(f"Warning: Removing non-serializable list item with type {type(item)}")
                continue
        return cleaned
    else:
        return data


def save_state():
    """Сохраняет состояние в файл"""
    try:
        # Вместо предварительной очистки, сохраняем исходные данные,
        # и используем json_serializer для корректной сериализации
        state_data = {
            "scheduled_posts": scheduled_posts,
            "planning_states": planning_states,
            "timestamp": datetime.now().isoformat(),
        }
        
        # Проверяем, что данные можно сериализовать
        serialized_data = json.dumps(
            state_data, 
            ensure_ascii=False, 
            indent=2, 
            default=json_serializer
        )
        
        # Сначала записываем во временный файл
        temp_file = f"{STATE_FILE}.tmp"
        with open(temp_file, "w", encoding="utf-8") as f:
            f.write(serialized_data)
            
        # Если временный файл создан успешно, заменяем им основной файл
        if os.path.exists(temp_file):
            if os.path.exists(STATE_FILE):
                os.remove(STATE_FILE)
            os.rename(temp_file, STATE_FILE)
            print("State saved successfully")
        else:
            raise Exception("Failed to create temporary state file")
            
    except Exception as e:
        print(f"Error saving state: {e}")
        # Создаем резервную копию поврежденного файла
        if os.path.exists(STATE_FILE):
            backup_name = f"{STATE_FILE}.error_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            try:
                os.rename(STATE_FILE, backup_name)
                print(f"Corrupted state file backed up as {backup_name}")
            except Exception as backup_error:
                print(f"Error creating backup: {backup_error}")


def load_state():
    """Загружает состояние из файла"""
    global scheduled_posts, planning_states
    try:
        if os.path.exists(STATE_FILE):
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                content = f.read()
                # Проверяем, что файл содержит валидный JSON
                if not content.strip():
                    print("State file is empty, using default state")
                    return
                    
                state_data = json.loads(content)
                scheduled_posts.clear()
                scheduled_posts.update(state_data.get("scheduled_posts", {}))
                planning_states.clear()
                planning_states.update(state_data.get("planning_states", {}))
                print("State loaded successfully")
    except Exception as e:
        print(f"Error loading state: {e}")
        # Создаем резервную копию поврежденного файла
        if os.path.exists(STATE_FILE):
            backup_name = f"{STATE_FILE}.error_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            try:
                os.rename(STATE_FILE, backup_name)
                print(f"Corrupted state file backed up as {backup_name}")
            except Exception as backup_error:
                print(f"Error creating backup: {backup_error}")
        
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
