import os
from dotenv import load_dotenv
import logging

load_dotenv()
log = logging.getLogger("tg-vk-bot")

BOT_TOKEN = os.getenv("BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL_TEXT = os.getenv("OPENAI_MODEL_TEXT", "gpt-4o")  # Модель для генерации текста постов
OPENAI_MODEL_PROMPT = os.getenv("OPENAI_MODEL_PROMPT", "gpt-4o")  # Модель для создания промптов изображений
YANDEX_API_KEY = os.getenv("YANDEX_API_KEY")
YANDEX_FOLDER_ID = os.getenv("YANDEX_FOLDER_ID")
TELEGRAM_CHANNEL_ID = os.getenv("TELEGRAM_CHANNEL_ID")
VK_ACCESS_TOKEN = os.getenv("VK_ACCESS_TOKEN")
VK_GROUP_ID = os.getenv("VK_GROUP_ID")
VK_API_VERSION = os.getenv("VK_API_VERSION", "5.199")

REQUIRED_ENV = [
    ("BOT_TOKEN", BOT_TOKEN),
    ("OPENAI_API_KEY", OPENAI_API_KEY),
    ("YANDEX_API_KEY", YANDEX_API_KEY),
    ("YANDEX_FOLDER_ID", YANDEX_FOLDER_ID),
    ("TELEGRAM_CHANNEL_ID", TELEGRAM_CHANNEL_ID),
    ("VK_ACCESS_TOKEN", VK_ACCESS_TOKEN),
    ("VK_GROUP_ID", VK_GROUP_ID),
]
missing = [name for name, val in REQUIRED_ENV if not val]
if missing:
    raise RuntimeError(f"Отсутствуют переменные окружения: {', '.join(missing)}")