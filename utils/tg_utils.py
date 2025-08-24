from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

def clean_markdown(text: str) -> str:
    """
    Убирает Markdown разметку из текста для публикации в каналы.
    Удаляет символы: *, **, #, ###, и т.д.
    """
    import re
    
    if not text:
        return ""
    
    # Убираем жирный текст (**text** и __text__)
    text = re.sub(r'\*\*(.*?)\*\*', r'\1', text)
    text = re.sub(r'__(.*?)__', r'\1', text)
    
    # Убираем курсив (*text* и _text_)
    text = re.sub(r'\*(.*?)\*', r'\1', text)
    text = re.sub(r'_(.*?)_', r'\1', text)
    
    # Убираем заголовки (# ## ###)
    text = re.sub(r'^#{1,6}\s*', '', text, flags=re.MULTILINE)
    
    # Убираем оставшиеся одиночные * и #
    text = re.sub(r'(?<!\S)\*(?!\S)', '', text)  # одиночные *
    text = re.sub(r'(?<!\S)#(?!\S)', '', text)   # одиночные #
    
    return text.strip()

def truncate_caption(text: str, max_len: int = 1024) -> str:
    """Обрезает текст для caption (резервная функция для VK fallback)"""
    if text is None:
        return ""
    if len(text) <= max_len:
        return text
    truncated = text[:max_len]
    last_dot = truncated.rfind('.')
    return truncated[:last_dot+1] if last_dot != -1 else truncated + "..."

def smart_vk_text(text: str) -> str:
    """
    Умная обработка текста для VK:
    - Если текст до 15000 символов - отправляем полностью
    - Если больше - обрезаем красиво
    """
    if not text:
        return ""
    
    clean_text = clean_markdown(text)
    
    # VK поддерживает до 16000 символов, оставляем запас
    if len(clean_text) <= 15000:
        return clean_text
    
    # Если текст слишком длинный - обрезаем красиво
    truncated = clean_text[:14500]  # Оставляем место для "..."
    
    # Ищем последнее предложение
    last_sentence = truncated.rfind('.')
    if last_sentence > 10000:  # Если есть предложение в разумных пределах
        return truncated[:last_sentence + 1] + "\n\n... (продолжение в комментариях)"
    
    # Если нет - ищем последний абзац
    last_paragraph = truncated.rfind('\n\n')
    if last_paragraph > 8000:
        return truncated[:last_paragraph] + "\n\n... (продолжение в комментариях)"
    
    # В крайнем случае - просто обрезаем
    return truncated + "..."

def send_post_with_image(bot, chat_id, text: str, image_bytes: bytes, reply_markup=None, parse_mode=None):
    """
    Отправляет пост с изображением без ограничений на длину текста.
    Если текст длинный - отправляет отдельно изображение и текст.
    """
    import io
    
    # Если текст короткий - отправляем как caption
    if len(text) <= 1000:
        try:
            return bot.send_photo(
                chat_id,
                io.BytesIO(image_bytes),
                caption=text,
                reply_markup=reply_markup,
                parse_mode=parse_mode
            )
        except Exception as e:
            # Если не удалось с caption, отправляем отдельно
            pass
    
    # Отправляем изображение и текст отдельно
    try:
        # Сначала изображение
        bot.send_photo(chat_id, io.BytesIO(image_bytes))
        
        # Затем текст с кнопками
        return bot.send_message(
            chat_id,
            text,
            reply_markup=reply_markup,
            parse_mode=parse_mode
        )
    except Exception as e:
        # В крайнем случае отправляем только текст
        return bot.send_message(
            chat_id,
            f"❌ Ошибка отправки изображения\n\n{text}",
            reply_markup=reply_markup,
            parse_mode=parse_mode
        )

def action_keyboard() -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup()
    kb.row(
        InlineKeyboardButton("✍️ Изменить текст", callback_data="edit_text"),
        InlineKeyboardButton("🎨 Изменить картинку", callback_data="edit_image"),
    )
    kb.row(
        InlineKeyboardButton("📢 В Telegram", callback_data="publish_post"),
        InlineKeyboardButton("🖼️ В VK", callback_data="publish_vk_photo"),
    )
    kb.row(
        InlineKeyboardButton("📝 В VK (только текст)", callback_data="publish_vk_text"),
    )
    return kb

def topics_approval_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура для одобрения тем"""
    kb = InlineKeyboardMarkup()
    kb.row(
        InlineKeyboardButton("✅ Одобрить темы", callback_data="approve_topics"),
        InlineKeyboardButton("✍️ Изменить темы", callback_data="edit_topics"),
    )
    kb.row(
        InlineKeyboardButton("📝 Написать свои темы", callback_data="custom_topics")
    )
    return kb

def posts_approval_keyboard(post_index: int, total_posts: int) -> InlineKeyboardMarkup:
    """Клавиатура для одобрения постов"""
    kb = InlineKeyboardMarkup()
    kb.row(
        InlineKeyboardButton("✅ Одобрить", callback_data=f"approve_post_{post_index}"),
        InlineKeyboardButton("✍️ Изменить", callback_data=f"edit_post_{post_index}"),
    )
    if post_index < total_posts - 1:
        kb.row(InlineKeyboardButton("⏭️ Следующий пост", callback_data=f"next_post_{post_index + 1}"))
    else:
        kb.row(InlineKeyboardButton("🎯 Завершить планирование", callback_data="finish_planning"))
    return kb

def admin_keyboard() -> InlineKeyboardMarkup:
    """Админская клавиатура"""
    kb = InlineKeyboardMarkup()
    kb.row(
        InlineKeyboardButton("📅 Статус планирования", callback_data="admin_status"),
        InlineKeyboardButton("🗓️ Генерировать темы", callback_data="admin_generate_topics"),
    )
    kb.row(
        InlineKeyboardButton("📋 Очередь постов", callback_data="admin_queue"),
        InlineKeyboardButton("📊 Статистика", callback_data="admin_stats"),
    )
    return kb