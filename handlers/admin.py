# handlers/admin.py
from telebot.types import Message, CallbackQuery
import logging
from datetime import datetime

from state import scheduled_posts, store_lock, save_state
from utils.tg_utils import admin_keyboard, topics_approval_keyboard
from utils.openai_utils import generate_topics
from scheduler import content_scheduler

log = logging.getLogger("tg-vk-bot")

def register(bot):
    """Регистрирует админские команды"""
    
    @bot.message_handler(commands=["admin"])
    def admin_panel(msg: Message):
        """Админская панель"""
        chat_id = msg.chat.id
        
        # Устанавливаем этот чат как админский
        if content_scheduler:
            content_scheduler.set_admin_chat_id(chat_id)
        
        message = "🔧 **Админская панель**\n\n"
        message += "Управление планированием контента и публикацией постов."
        
        bot.send_message(
            chat_id,
            message,
            reply_markup=admin_keyboard(),
            parse_mode='Markdown'
        )
    
    @bot.message_handler(commands=["start_scheduler"])
    def start_scheduler_cmd(msg: Message):
        """Запускает планировщик"""
        chat_id = msg.chat.id
        
        if content_scheduler:
            content_scheduler.set_admin_chat_id(chat_id)
            content_scheduler.start_scheduler()
            bot.send_message(
                chat_id,
                "✅ Планировщик запущен!\n\n"
                "📅 Расписание:\n"
                "• Воскресенье 16:00 МСК - генерация тем\n"
                "• Пн/Ср/Пт 19:00 МСК - публикация постов"
            )
        else:
            bot.send_message(chat_id, "❌ Ошибка: планировщик не инициализирован")
    
    @bot.message_handler(commands=["stop_scheduler"])
    def stop_scheduler_cmd(msg: Message):
        """Останавливает планировщик"""
        chat_id = msg.chat.id
        
        if content_scheduler:
            content_scheduler.stop_scheduler()
            bot.send_message(chat_id, "⏹️ Планировщик остановлен")
        else:
            bot.send_message(chat_id, "❌ Планировщик не найден")
    
    @bot.callback_query_handler(func=lambda c: c.data == "admin_status")
    def show_status(call: CallbackQuery):
        """Показывает статус планирования"""
        chat_id = call.message.chat.id
        
        with store_lock:
            pending_topics = scheduled_posts.get("pending_topics")
            approved_topics = scheduled_posts.get("approved_topics", [])
            pending_posts = scheduled_posts.get("pending_posts", [])
            approved_posts = scheduled_posts.get("approved_posts", [])
            published_posts = scheduled_posts.get("published_posts", [])
        
        message = "📊 **Статус планирования**\n\n"
        
        # Темы
        if pending_topics and pending_topics["status"] == "waiting_approval":
            message += f"🟡 Темы ожидают одобрения: {len(pending_topics['topics'])}\n"
        elif approved_topics:
            message += f"✅ Одобренные темы: {len(approved_topics)}\n"
        else:
            message += "⚪ Нет активных тем\n"
        
        # Посты
        message += f"🟡 Посты на согласовании: {len(pending_posts)}\n"
        message += f"✅ Посты в очереди: {len(approved_posts)}\n"
        message += f"📤 Опубликованные посты: {len(published_posts)}\n\n"
        
        # Планировщик
        scheduler_status = "🟢 Работает" if (content_scheduler and content_scheduler.running) else "🔴 Остановлен"
        message += f"🤖 Планировщик: {scheduler_status}\n"
        
        # Следующая публикация
        if approved_posts:
            message += f"\n📅 Следующая публикация: ближайший Пн/Ср/Пт в 19:00 МСК"
        
        bot.send_message(chat_id, message, parse_mode='Markdown')
        bot.answer_callback_query(call.id)
    
    @bot.callback_query_handler(func=lambda c: c.data == "admin_generate_topics")
    def generate_topics_manually(call: CallbackQuery):
        """Ручная генерация тем"""
        chat_id = call.message.chat.id
        
        bot.answer_callback_query(call.id, "🔄 Генерирую темы...")
        
        try:
            topics = generate_topics()
            
            with store_lock:
                scheduled_posts["pending_topics"] = {
                    "topics": topics,
                    "status": "waiting_approval",
                    "generated_at": datetime.now().isoformat()
                }
                save_state()
            
            message = "🗓️ **Сгенерированные темы:**\n\n"
            for i, topic in enumerate(topics, 1):
                message += f"{i}. {topic}\n\n"
            message += "Выберите действие:"
            
            bot.send_message(
                chat_id,
                message,
                reply_markup=topics_approval_keyboard(),
                parse_mode='Markdown'
            )
            
        except Exception as e:
            log.exception("Error generating topics manually")
            bot.send_message(chat_id, f"❌ Ошибка генерации тем: {e}")
    
    @bot.callback_query_handler(func=lambda c: c.data == "admin_queue")
    def show_queue(call: CallbackQuery):
        """Показывает очередь постов"""
        chat_id = call.message.chat.id
        
        with store_lock:
            approved_posts = scheduled_posts.get("approved_posts", [])
        
        if not approved_posts:
            bot.send_message(chat_id, "📋 Очередь публикации пуста")
            bot.answer_callback_query(call.id)
            return
        
        message = f"📋 **Очередь публикации ({len(approved_posts)} постов)**\n\n"
        
        for i, post in enumerate(approved_posts, 1):
            topic = post.get("topic", "Без темы")[:50]
            message += f"{i}. {topic}...\n"
        
        message += f"\n📅 Публикация: Пн/Ср/Пт в 19:00 МСК"
        
        bot.send_message(chat_id, message, parse_mode='Markdown')
        bot.answer_callback_query(call.id)
    
    @bot.callback_query_handler(func=lambda c: c.data == "admin_stats")
    def show_stats(call: CallbackQuery):
        """Показывает статистику"""
        chat_id = call.message.chat.id
        
        with store_lock:
            published_posts = scheduled_posts.get("published_posts", [])
            approved_posts = scheduled_posts.get("approved_posts", [])
        
        message = "📊 **Статистика**\n\n"
        message += f"📤 Всего опубликовано: {len(published_posts)}\n"
        message += f"⏳ В очереди: {len(approved_posts)}\n"
        
        if published_posts:
            # Последняя публикация
            last_post = published_posts[-1]
            last_topic = last_post.get("topic", "Неизвестно")[:50]
            message += f"\n📝 Последний пост: {last_topic}...\n"
            
            # Статистика по неделям
            from datetime import datetime, timedelta
            now = datetime.now()
            week_ago = now - timedelta(days=7)
            
            recent_posts = [
                p for p in published_posts 
                if p.get("publish_date") and 
                datetime.fromisoformat(p["publish_date"].replace("Z", "+00:00")) > week_ago
            ]
            
            message += f"📈 За последнюю неделю: {len(recent_posts)} постов"
        
        bot.send_message(chat_id, message, parse_mode='Markdown')
        bot.answer_callback_query(call.id)
