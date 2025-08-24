# handlers/content_planning.py
from telebot.types import Message, CallbackQuery
import logging
from datetime import datetime

from state import scheduled_posts, planning_states, store_lock, save_state
from utils.openai_utils import edit_topics, generate_text, generate_image_prompt
from utils.yandex_utils import generate_image_bytes_with_yc
from utils.tg_utils import (
    topics_approval_keyboard,
    posts_approval_keyboard,
    send_post_with_image,
)

log = logging.getLogger("tg-vk-bot")


def register(bot):
    """Регистрирует обработчики для планирования контента"""

    # Обработчики для одобрения тем
    @bot.callback_query_handler(func=lambda c: c.data == "approve_topics")
    def approve_topics(call: CallbackQuery):
        chat_id = call.message.chat.id

        with store_lock:
            pending = scheduled_posts.get("pending_topics")
            if not pending or pending["status"] != "waiting_approval":
                bot.answer_callback_query(call.id, "❌ Нет тем для одобрения")
                return

            # Переносим темы в одобренные
            scheduled_posts["approved_topics"] = pending["topics"]
            scheduled_posts["pending_topics"] = None
            save_state()

        bot.answer_callback_query(call.id, "✅ Темы одобрены!")
        bot.send_message(chat_id, "✅ Темы одобрены! Начинаю генерацию постов...", reply_markup=None)

        # Запускаем генерацию постов
        _generate_posts_for_topics(bot, chat_id)

    @bot.callback_query_handler(func=lambda c: c.data == "edit_topics")
    def ask_edit_topics(call: CallbackQuery):
        chat_id = call.message.chat.id
        planning_states[chat_id] = {"action": "waiting_topics_edit"}

        bot.answer_callback_query(call.id, "✏️ Ожидаю инструкции")
        bot.send_message(chat_id, "Опишите, как изменить темы (стиль, направление, конкретные пожелания):")

    @bot.callback_query_handler(func=lambda c: c.data == "custom_topics")
    def ask_custom_topics(call: CallbackQuery):
        chat_id = call.message.chat.id
        planning_states[chat_id] = {"action": "waiting_custom_topics"}

        bot.answer_callback_query(call.id, "✏️ Ожидаю ваши темы")
        bot.send_message(chat_id, "Напишите 3 темы для постов, каждую с новой строки:")

    # Обработчики для одобрения постов
    @bot.callback_query_handler(func=lambda c: c.data.startswith("approve_post_"))
    def approve_post(call: CallbackQuery):
        chat_id = call.message.chat.id
        post_index = int(call.data.split("_")[-1])

        with store_lock:
            pending_posts = scheduled_posts.get("pending_posts", [])
            if post_index >= len(pending_posts):
                bot.answer_callback_query(call.id, "❌ Пост не найден")
                return

            # Одобряем пост
            post = pending_posts[post_index]
            post["status"] = "approved"

            if "approved_posts" not in scheduled_posts:
                scheduled_posts["approved_posts"] = []
            scheduled_posts["approved_posts"].append(post)
            save_state()

        bot.answer_callback_query(call.id, "✅ Пост одобрен!")

        # Показываем следующий пост или завершаем
        _show_next_post_or_finish(bot, chat_id, post_index)

    @bot.callback_query_handler(func=lambda c: c.data.startswith("edit_post_"))
    def ask_edit_post(call: CallbackQuery):
        chat_id = call.message.chat.id
        post_index = int(call.data.split("_")[-1])

        planning_states[chat_id] = {"action": "waiting_post_edit", "post_index": post_index}

        bot.answer_callback_query(call.id, "✏️ Ожидаю инструкции")
        bot.send_message(chat_id, "Опишите, как изменить этот пост (стиль, содержание, акценты):")

    @bot.callback_query_handler(func=lambda c: c.data.startswith("next_post_"))
    def show_next_post(call: CallbackQuery):
        chat_id = call.message.chat.id
        post_index = int(call.data.split("_")[-1])

        _show_post_for_approval(bot, chat_id, post_index)
        bot.answer_callback_query(call.id)

    @bot.callback_query_handler(func=lambda c: c.data == "finish_planning")
    def finish_planning(call: CallbackQuery):
        chat_id = call.message.chat.id

        with store_lock:
            approved_count = len(scheduled_posts.get("approved_posts", []))
            # Очищаем pending_posts после завершения
            scheduled_posts["pending_posts"] = []
            save_state()

        bot.answer_callback_query(call.id, "🎯 Планирование завершено!")

        message = "🎯 **Планирование завершено!**\n\n"
        message += f"✅ Одобрено постов: {approved_count}\n"
        message += "📅 Посты будут опубликованы по расписанию:\n"
        message += "• Понедельник 19:00 МСК\n"
        message += "• Среда 19:00 МСК\n"
        message += "• Пятница 19:00 МСК\n\n"
        message += "Используйте /admin для управления."

        bot.send_message(chat_id, message, parse_mode="Markdown")


def handle_planning_message(bot, msg: Message):
    """Обрабатывает сообщения в процессе планирования"""
    chat_id = msg.chat.id
    state = planning_states.get(chat_id, {})
    action = state.get("action")

    if action == "waiting_topics_edit":
        _handle_topics_edit(bot, msg)
    elif action == "waiting_custom_topics":
        _handle_custom_topics(bot, msg)
    elif action == "waiting_post_edit":
        _handle_post_edit(bot, msg)


def _handle_topics_edit(bot, msg: Message):
    """Обрабатывает редактирование тем"""
    chat_id = msg.chat.id
    instruction = msg.text.strip()

    if not instruction:
        bot.send_message(chat_id, "Пожалуйста, опишите, как изменить темы.")
        return

    with store_lock:
        pending = scheduled_posts.get("pending_topics")
        if not pending:
            bot.send_message(chat_id, "❌ Нет тем для редактирования.")
            planning_states.pop(chat_id, None)
            return

        current_topics = pending["topics"]

    try:
        bot.send_message(chat_id, "🔄 Редактирую темы...")
        new_topics = edit_topics(current_topics, instruction)

        with store_lock:
            scheduled_posts["pending_topics"]["topics"] = new_topics
            save_state()

        message = "✏️ **Отредактированные темы:**\n\n"
        for i, topic in enumerate(new_topics, 1):
            message += f"{i}. {topic}\n\n"
        message += "Выберите действие:"

        bot.send_message(chat_id, message, reply_markup=topics_approval_keyboard(), parse_mode="Markdown")

    except Exception as e:
        log.exception("Error editing topics")
        bot.send_message(chat_id, f"❌ Ошибка редактирования тем: {e}")

    planning_states.pop(chat_id, None)


def _handle_custom_topics(bot, msg: Message):
    """Обрабатывает пользовательские темы"""
    chat_id = msg.chat.id
    text = msg.text.strip()

    if not text:
        bot.send_message(chat_id, "Пожалуйста, напишите темы.")
        return

    # Разбираем темы
    topics = [topic.strip() for topic in text.split("\n") if topic.strip()]

    if len(topics) < 3:
        bot.send_message(chat_id, f"Нужно минимум 3 темы, получено: {len(topics)}. Попробуйте еще раз.")
        return

    # Берем первые 3 темы
    topics = topics[:3]

    with store_lock:
        scheduled_posts["pending_topics"] = {
            "topics": topics,
            "status": "waiting_approval",
            "generated_at": datetime.now().isoformat(),
        }
        save_state()

    message = "📝 **Ваши темы:**\n\n"
    for i, topic in enumerate(topics, 1):
        message += f"{i}. {topic}\n\n"
    message += "Выберите действие:"

    bot.send_message(chat_id, message, reply_markup=topics_approval_keyboard(), parse_mode="Markdown")

    planning_states.pop(chat_id, None)


def _handle_post_edit(bot, msg: Message):
    """Обрабатывает редактирование поста"""
    chat_id = msg.chat.id
    instruction = msg.text.strip()
    state = planning_states.get(chat_id, {})
    post_index = state.get("post_index", 0)

    if not instruction:
        bot.send_message(chat_id, "Пожалуйста, опишите, как изменить пост.")
        return

    with store_lock:
        pending_posts = scheduled_posts.get("pending_posts", [])
        if post_index >= len(pending_posts):
            bot.send_message(chat_id, "❌ Пост не найден.")
            planning_states.pop(chat_id, None)
            return

        post = pending_posts[post_index]

    try:
        bot.send_message(chat_id, "🔄 Редактирую пост...")

        # Редактируем текст поста
        from utils.openai_utils import _openai_chat

        prompt = (
            "Отредактируй текст поста строго по инструкции. Сохрани факты, улучшай структуру и ясность. "
            "Верни только готовый текст без пояснений.\n\n"
            f"ТЕКСТ:\n{post['text']}\n\nИНСТРУКЦИЯ:\n{instruction}"
        )
        new_text = _openai_chat([{"role": "user", "content": prompt}], "gpt-4o")

        # Генерируем новое изображение если нужно
        new_prompt = generate_image_prompt(new_text)
        new_image_bytes = generate_image_bytes_with_yc(new_prompt)

        # Обновляем пост
        with store_lock:
            from scheduler import ScheduledPost

            old_post_data = pending_posts[post_index]
            updated_post = ScheduledPost.from_dict(old_post_data)
            updated_post.text = new_text
            updated_post.image_bytes = new_image_bytes
            pending_posts[post_index] = updated_post.to_dict()
            save_state()

        # Показываем обновленный пост без ограничений
        _show_post_for_approval(bot, chat_id, post_index)

    except Exception as e:
        log.exception("Error editing post")
        bot.send_message(chat_id, f"❌ Ошибка редактирования поста: {e}")

    planning_states.pop(chat_id, None)


def _generate_posts_for_topics(bot, chat_id: int):
    """Генерирует посты для одобренных тем"""
    try:
        with store_lock:
            topics = scheduled_posts.get("approved_topics", [])

        if not topics:
            bot.send_message(chat_id, "❌ Нет одобренных тем.")
            return

        bot.send_message(chat_id, f"🔄 Генерирую {len(topics)} постов, это займет около минуты...")

        posts = []
        for i, topic in enumerate(topics, 1):
            try:
                bot.send_message(chat_id, f"📝 Генерирую пост {i}/{len(topics)}: {topic[:50]}...")

                # Генерируем текст поста
                text = generate_text(topic)

                # Генерируем промпт для изображения
                image_prompt = generate_image_prompt(text)

                # Генерируем изображение
                image_bytes = generate_image_bytes_with_yc(image_prompt)

                # Создаем объект поста
                from scheduler import ScheduledPost

                post = ScheduledPost(
                    topic=topic, text=text, image_bytes=image_bytes, publish_date=None, status="pending"
                )
                posts.append(post.to_dict())

            except Exception as e:
                log.exception(f"Error generating post for topic: {topic}")
                bot.send_message(chat_id, f"❌ Ошибка генерации поста для темы '{topic[:30]}...': {e}")

        if posts:
            with store_lock:
                scheduled_posts["pending_posts"] = posts
                save_state()

            bot.send_message(chat_id, f"✅ Сгенерировано {len(posts)} постов! Начинаем согласование...")

            # Показываем первый пост для одобрения
            _show_post_for_approval(bot, chat_id, 0)
        else:
            bot.send_message(chat_id, "❌ Не удалось сгенерировать ни одного поста.")

    except Exception as e:
        log.exception("Error generating posts")
        bot.send_message(chat_id, f"❌ Ошибка генерации постов: {e}")


def _show_post_for_approval(bot, chat_id: int, post_index: int):
    """Показывает пост для одобрения"""
    with store_lock:
        pending_posts = scheduled_posts.get("pending_posts", [])

    if post_index >= len(pending_posts):
        bot.send_message(chat_id, "❌ Пост не найден.")
        return

    post_data = pending_posts[post_index]
    total_posts = len(pending_posts)

    try:
        from scheduler import ScheduledPost

        post = ScheduledPost.from_dict(post_data)

        full_text = f"📝 **Пост {post_index + 1} из {total_posts}**\n\n"
        full_text += f"**Тема:** {post.topic}\n\n"
        full_text += post.text

        send_post_with_image(
            bot,
            chat_id,
            full_text,
            post.image_bytes,
            reply_markup=posts_approval_keyboard(post_index, total_posts),
            parse_mode="Markdown",
        )
    except Exception as e:
        log.exception("Error showing post for approval")
        bot.send_message(chat_id, f"❌ Ошибка отображения поста: {e}")


def _show_next_post_or_finish(bot, chat_id: int, current_index: int):
    """Показывает следующий пост или завершает планирование"""
    with store_lock:
        pending_posts = scheduled_posts.get("pending_posts", [])

    next_index = current_index + 1

    if next_index < len(pending_posts):
        _show_post_for_approval(bot, chat_id, next_index)
    else:
        # Все посты просмотрены
        approved_count = len(scheduled_posts.get("approved_posts", []))

        message = "🎯 **Все посты просмотрены!**\n\n"
        message += f"✅ Одобрено постов: {approved_count}\n\n"

        if approved_count > 0:
            message += "📅 Посты будут опубликованы по расписанию:\n"
            message += "• Понедельник 19:00 МСК\n"
            message += "• Среда 19:00 МСК\n"
            message += "• Пятница 19:00 МСК\n\n"
            message += "Используйте /admin для управления."
        else:
            message += "Для публикации нужно одобрить хотя бы один пост."

        bot.send_message(chat_id, message, parse_mode="Markdown")
