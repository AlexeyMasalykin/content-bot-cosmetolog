# handlers/general.py
from telebot.types import Message
from utils.openai_utils import generate_text, generate_image_prompt
from utils.yandex_utils import generate_image_bytes_with_yc
from utils.tg_utils import truncate_caption, action_keyboard, send_post_with_image
from state import user_drafts, store_lock, user_states
import logging
import io

log = logging.getLogger("tg-vk-bot")

def register(bot):
    @bot.message_handler(commands=["start"])
    def cmd_start(msg: Message):
        welcome_text = (
            "🤖 **Добро пожаловать в Content Bot!**\n\n"
            "**Режимы работы:**\n"
            "• 📝 **Быстрый пост** - просто напишите тему\n"
            "• 📅 **Планирование** - используйте /admin\n\n"
            "**Команды:**\n"
            "• /post - создать пост по теме\n"
            "• /draft - показать текущий черновик\n"
            "• /admin - админская панель\n"
            "• /help - подробная справка\n\n"
            "💡 **Просто напишите тему поста, и я создам экспертный контент!**\n\n"
            "**Примеры тем:**\n"
            "• _Правда ли, что кожа привыкает к косметике_\n"
            "• _Зимний уход: главные правила_\n"
            "• _Витамин С для лица: мифы и факты_"
        )
        bot.send_message(msg.chat.id, welcome_text, parse_mode='Markdown')
    
    @bot.message_handler(commands=["post"])
    def cmd_post(msg: Message):
        bot.send_message(
            msg.chat.id, 
            "📝 **Быстрое создание поста**\n\n"
            "Напишите тему для поста, и я создам текст с изображением:",
            parse_mode='Markdown'
        )
    
    @bot.message_handler(commands=["help"])
    def cmd_help(msg: Message):
        help_text = (
            "📚 Справка по Content Bot\n\n"
            "🚀 Быстрое создание постов:\n"
            "1. Напишите тему (миф, вопрос, процедуру)\n"
            "2. Получите экспертный пост с научными фактами\n"
            "3. Отредактируйте при необходимости\n"
            "4. Опубликуйте в Telegram или VK\n\n"
            "📝 Формат постов:\n"
            "• Вступление-крючок (вопрос, миф)\n"
            "• Факты и советы (структурированно)\n"
            "• Вывод с мотивацией\n"
            "• Дружелюбный, но экспертный стиль\n\n"
            "📅 Автоматическое планирование:\n"
            "• /admin - панель управления\n"
            "• /start_scheduler - запуск планировщика\n"
            "• Генерация тем: Вс 16:00 МСК\n"
            "• Публикация: Пн/Ср/Пт 19:00 МСК\n\n"
            "✏️ Редактирование:\n"
            "• Изменить текст - отредактировать содержание\n"
            "• Изменить картинку - новое изображение\n\n"
            "📤 Публикация:\n"
            "• В Telegram - с изображением\n"
            "• В VK - с изображением\n\n"
            "Просто напишите тему и начните создавать контент! 🎯"
        )
        bot.send_message(msg.chat.id, help_text)
    
    @bot.message_handler(commands=["draft", "черновик"])
    def cmd_draft(msg: Message):
        user_id = msg.chat.id
        
        with store_lock:
            draft = user_drafts.get(user_id)
        
        if not draft:
            bot.send_message(
                user_id,
                "📝 **Нет активного черновика**\n\n"
                "Создайте пост, написав любую тему!",
                parse_mode='Markdown'
            )
            return
        
        try:
            topic = draft.get("topic", "Неизвестная тема")
            full_text = f"📝 **Текущий черновик**\n"
            full_text += f"🏷️ Тема: _{topic}_\n\n"
            full_text += draft["text"]
            
            send_post_with_image(
                bot,
                user_id,
                full_text,
                draft["image_bytes"],
                reply_markup=action_keyboard(),
                parse_mode='Markdown'
            )
        except Exception as e:
            log.exception("Error showing draft")
            bot.send_message(
                user_id,
                f"❌ Ошибка отображения черновика: {e}"
            )
    
    # Обработчик неизвестных команд
    @bot.message_handler(func=lambda m: m.content_type == 'text' and m.text.startswith('/'))
    def unknown_command(msg: Message):
        command = msg.text.split()[0]
        bot.send_message(
            msg.chat.id,
            f"❓ **Неизвестная команда:** `{command}`\n\n"
            f"**Доступные команды:**\n"
            f"• /start - главное меню\n"
            f"• /post - создать пост\n"
            f"• /draft - показать черновик\n"
            f"• /admin - админская панель\n"
            f"• /help - подробная справка\n\n"
            f"Или просто напишите тему поста!",
            parse_mode='Markdown'
        )

    @bot.message_handler(func=lambda m: m.content_type == 'text' and not m.text.startswith('/'))
    def on_text(msg: Message):
        user_id = msg.chat.id
        text = (msg.text or "").strip()
        
        # Дополнительная защита от команд
        if text.startswith('/'):
            return
        
        state = user_states.get(user_id)
        
        # Проверяем состояния планирования
        from state import planning_states
        if user_id in planning_states:
            from handlers.content_planning import handle_planning_message
            handle_planning_message(bot, msg)
            return
        
        # Существующие состояния
        if state == "waiting_edit_hint":
            from handlers.edit_text import apply_edit_instruction
            apply_edit_instruction(bot, msg)
            return
        if state == "waiting_image_hint":
            from handlers.edit_image import apply_image_instruction
            apply_image_instruction(bot, msg)
            return
        
        # Обычная генерация поста
        handle_topic(bot, msg)

def handle_topic(bot, msg: Message):
    topic = (msg.text or "").strip()
    if not topic:
        bot.send_message(
            msg.chat.id, 
            "🤔 Пожалуйста, укажите тему поста.\n\n"
            "**Примеры хороших тем:**\n"
            "• *Правда ли, что кожа привыкает к косметике*\n"
            "• *Зимний уход: 5 главных правил*\n"
            "• *Витамин С для лица: мифы и факты*\n"
            "• *Как правильно очищать кожу*",
            parse_mode='Markdown'
        )
        return

    # Показываем индикатор режима
    status_msg = bot.send_message(
        msg.chat.id, 
        f"🚀 **Быстрый режим**\n"
        f"📝 Тема: _{topic}_\n\n"
        f"⏳ Генерирую пост и изображение...\n"
        f"Это займёт ~10–20 секунд",
        parse_mode='Markdown'
    )
    
    try:
        # Генерируем контент
        text = generate_text(topic)
        prompt = generate_image_prompt(text)
        image_bytes = generate_image_bytes_with_yc(prompt)
        
        # Удаляем статусное сообщение
        try:
            bot.delete_message(msg.chat.id, status_msg.message_id)
        except:
            pass  # Игнорируем ошибки удаления
            
    except Exception as e:
        log.exception("Ошибка генерации")
        bot.edit_message_text(
            f"❌ **Ошибка генерации**\n\n"
            f"Не удалось создать пост по теме: _{topic}_\n"
            f"Ошибка: `{str(e)[:100]}...`\n\n"
            f"Попробуйте другую тему или повторите попытку.",
            msg.chat.id, 
            status_msg.message_id,
            parse_mode='Markdown'
        )
        return

    # Сохраняем черновик
    with store_lock:
        user_drafts[msg.chat.id] = {
            "text": text,
            "image_bytes": image_bytes,
            "topic": topic,
            "created_at": msg.date
        }

    try:
        # Отправляем готовый пост без ограничений длины
        full_text = f"✅ **Пост готов!**\n\n{text}"
        
        send_post_with_image(
            bot,
            msg.chat.id,
            full_text,
            image_bytes,
            reply_markup=action_keyboard(),
            parse_mode='Markdown'
        )
        
        # Дополнительная информация
        bot.send_message(
            msg.chat.id,
            "💡 **Что дальше?**\n"
            "• ✍️ Отредактируйте текст или изображение\n"
            "• 📢 Опубликуйте в Telegram или VK\n"
            "• Или напишите новую тему для следующего поста",
            parse_mode='Markdown'
        )
        
    except Exception as e:
        log.exception("Ошибка отправки предпросмотра")
        bot.send_message(
            msg.chat.id, 
            f"❌ **Ошибка отображения**\n\n"
            f"Пост создан, но не могу его показать: `{str(e)[:100]}...`\n\n"
            f"Попробуйте создать новый пост.",
            parse_mode='Markdown'
        )