# scheduler.py
import schedule
import time
import threading
import logging
from datetime import datetime, timedelta
import pytz
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
import json
import base64

from state import scheduled_posts, store_lock, save_state
from utils.openai_utils import generate_topics, generate_text, generate_image_prompt
from utils.yandex_utils import generate_image_bytes_with_yc
from config import TELEGRAM_CHANNEL_ID, VK_GROUP_ID

log = logging.getLogger("tg-vk-bot")

# Московское время
MSK = pytz.timezone('Europe/Moscow')

@dataclass
class ScheduledPost:
    topic: str
    text: str
    image_bytes: bytes
    publish_date: Optional[datetime] = None
    status: str = "pending"  # pending, published_tg, published_vk, completed
    post_id_tg: Optional[str] = None
    post_id_vk: Optional[str] = None
    
    def to_dict(self):
        """Конвертирует в словарь для сохранения в JSON"""
        data = asdict(self)
        # Кодируем bytes в base64 для JSON
        if isinstance(self.image_bytes, bytes):
            data['image_bytes'] = base64.b64encode(self.image_bytes).decode('utf-8')
        if self.publish_date:
            data['publish_date'] = self.publish_date.isoformat()
        return data
    
    @classmethod
    def from_dict(cls, data):
        """Создает объект из словаря"""
        if 'image_bytes' in data and isinstance(data['image_bytes'], str):
            data['image_bytes'] = base64.b64decode(data['image_bytes'].encode('utf-8'))
        if 'publish_date' in data and data['publish_date']:
            data['publish_date'] = datetime.fromisoformat(data['publish_date'])
        return cls(**data)

class ContentScheduler:
    def __init__(self, bot):
        self.bot = bot
        self.admin_chat_id = None  # Будет установлен при первом использовании
        self.running = False
        self.scheduler_thread = None
        
    def set_admin_chat_id(self, chat_id: int):
        """Устанавливает ID чата администратора"""
        self.admin_chat_id = chat_id
        log.info(f"Admin chat ID set to: {chat_id}")
    
    def start_scheduler(self):
        """Запускает планировщик в отдельном потоке"""
        if self.running:
            log.warning("Scheduler already running")
            return
            
        # Настройка расписания
        # Воскресенье 16:00 МСК - генерация тем
        schedule.every().sunday.at("16:00").do(self._generate_weekly_topics)
        
        # Понедельник, среда, пятница 19:00 МSК - публикация постов
        schedule.every().monday.at("19:00").do(self._publish_scheduled_post)
        schedule.every().wednesday.at("19:00").do(self._publish_scheduled_post)
        schedule.every().friday.at("19:00").do(self._publish_scheduled_post)
        
        self.running = True
        self.scheduler_thread = threading.Thread(target=self._run_scheduler, daemon=True)
        self.scheduler_thread.start()
        log.info("Content scheduler started")
    
    def stop_scheduler(self):
        """Останавливает планировщик"""
        self.running = False
        schedule.clear()
        if self.scheduler_thread:
            self.scheduler_thread.join(timeout=5)
        log.info("Content scheduler stopped")
    
    def _run_scheduler(self):
        """Основной цикл планировщика"""
        while self.running:
            try:
                # Конвертируем время в МСК для проверки расписания
                now_msk = datetime.now(MSK)
                schedule.run_pending()
                time.sleep(60)  # Проверяем каждую минуту
            except Exception as e:
                log.exception(f"Scheduler error: {e}")
                time.sleep(60)
    
    def _generate_weekly_topics(self):
        """Генерирует 3 темы на неделю"""
        if not self.admin_chat_id:
            log.error("Admin chat ID not set, cannot generate topics")
            return
            
        try:
            log.info("Generating weekly topics...")
            topics = generate_topics()
            
            # Сохраняем темы в состояние
            with store_lock:
                scheduled_posts["pending_topics"] = {
                    "topics": topics,
                    "status": "waiting_approval",
                    "generated_at": datetime.now(MSK).isoformat()
                }
                save_state()
            
            # Отправляем администратору
            message = "🗓️ **Темы на неделю:**\n\n"
            for i, topic in enumerate(topics, 1):
                message += f"{i}. {topic}\n\n"
            message += "Выберите действие:"
            
            from utils.tg_utils import topics_approval_keyboard
            self.bot.send_message(
                self.admin_chat_id,
                message,
                reply_markup=topics_approval_keyboard(),
                parse_mode='Markdown'
            )
            
        except Exception as e:
            log.exception("Error generating weekly topics")
            if self.admin_chat_id:
                self.bot.send_message(
                    self.admin_chat_id,
                    f"❌ Ошибка генерации тем: {e}"
                )
    
    def _publish_scheduled_post(self):
        """Публикует следующий запланированный пост"""
        if not self.admin_chat_id:
            log.error("Admin chat ID not set, cannot publish posts")
            return
            
        try:
            with store_lock:
                posts_queue = scheduled_posts.get("approved_posts", [])
                
            if not posts_queue:
                log.info("No posts in queue for publishing")
                return
                
            # Берем первый пост из очереди
            post_data = posts_queue[0]
            if isinstance(post_data, dict):
                post = ScheduledPost.from_dict(post_data)
            else:
                post = post_data
            
            if post.status != "pending":
                log.info(f"Post already processed: {post.status}")
                return
            
            log.info(f"Publishing post: {post.topic}")
            
            # Публикуем в Telegram с картинкой
            try:
                import io
                from utils.tg_utils import send_post_with_image, clean_markdown
                
                tg_msg = send_post_with_image(
                    self.bot,
                    TELEGRAM_CHANNEL_ID,
                    clean_markdown(post.text),
                    post.image_bytes
                )
                post.post_id_tg = str(tg_msg.message_id)
                post.status = "published_tg"
                log.info("Published to Telegram")
                
            except Exception as e:
                log.exception("Error publishing to Telegram")
                if self.admin_chat_id:
                    self.bot.send_message(
                        self.admin_chat_id,
                        f"❌ Ошибка публикации в Telegram: {e}"
                    )
            
            # Публикуем в VK с картинкой (обязательно)
            try:
                from utils.vk_utils import vk_publish_with_image_required, vk_post_url
                from utils.tg_utils import smart_vk_text
                
                # Публикация в VK с картинкой и умной обработкой текста
                post_id_vk = vk_publish_with_image_required(VK_GROUP_ID, post.image_bytes, smart_vk_text(post.text))
                post.post_id_vk = str(post_id_vk)
                post.status = "completed"
                
                # Формируем ссылку на пост в VK
                vk_url = vk_post_url(VK_GROUP_ID, post_id_vk)
                log.info(f"Published to VK: {vk_url}")
                
                # Уведомляем администратора
                if self.admin_chat_id:
                    self.bot.send_message(
                        self.admin_chat_id,
                        f"✅ Пост опубликован:\n"
                        f"📢 Telegram: опубликован\n"
                        f"🔗 VK: {vk_url}\n"
                        f"📝 Тема: {post.topic}"
                    )
                    
            except Exception as e:
                log.exception("Error publishing to VK")
                if self.admin_chat_id:
                    self.bot.send_message(
                        self.admin_chat_id,
                        f"❌ Ошибка публикации в VK: {e}"
                    )
            
            # Обновляем очередь постов
            with store_lock:
                posts_queue[0] = post.to_dict()
                if post.status == "completed":
                    # Удаляем опубликованный пост из очереди
                    scheduled_posts["approved_posts"] = posts_queue[1:]
                    # Добавляем в архив
                    if "published_posts" not in scheduled_posts:
                        scheduled_posts["published_posts"] = []
                    scheduled_posts["published_posts"].append(post.to_dict())
                else:
                    scheduled_posts["approved_posts"] = posts_queue
                save_state()
                    
        except Exception as e:
            log.exception("Error in scheduled publishing")
            if self.admin_chat_id:
                self.bot.send_message(
                    self.admin_chat_id,
                    f"❌ Ошибка автопубликации: {e}"
                )

# Глобальный экземпляр планировщика
content_scheduler = None

def init_scheduler(bot=None):
    """Инициализирует глобальный планировщик"""
    global content_scheduler
    if content_scheduler is None and bot is not None:
        content_scheduler = ContentScheduler(bot)
    return content_scheduler
