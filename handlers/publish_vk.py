# handlers/publish_vk.py
from telebot.types import CallbackQuery
from config import VK_GROUP_ID
from state import user_drafts, store_lock
from utils.tg_utils import smart_vk_text
from utils.vk_utils import vk_publish_text, vk_post_url, vk_publish_with_image_required
import logging

log = logging.getLogger("tg-vk-bot")


def register(bot):
    @bot.callback_query_handler(func=lambda c: c.data == "publish_vk_photo")
    def publish_vk_photo(call: CallbackQuery):
        chat_id = call.message.chat.id
        with store_lock:
            draft = user_drafts.get(chat_id)

        if not draft:
            bot.answer_callback_query(call.id, "❌ Нет черновика")
            return

        bot.answer_callback_query(call.id, "Публикуем в VK…")
        try:
            # Используем функцию с гарантированной публикацией с картинкой
            post_id = vk_publish_with_image_required(VK_GROUP_ID, draft["image_bytes"], smart_vk_text(draft["text"]))
            url = vk_post_url(VK_GROUP_ID, post_id)
            bot.send_message(chat_id, f"✅ Опубликовано с картинкой: {url}")
        except Exception as e:
            log.exception("VK post with image failed completely")
            bot.answer_callback_query(call.id, "❌ Ошибка публикации в VK")
            bot.send_message(chat_id, f"❌ Не удалось опубликовать пост с картинкой в VK: {e}")
            bot.send_message(chat_id, "🔧 Проверьте VK токен и права доступа")

    @bot.callback_query_handler(func=lambda c: c.data == "publish_vk_text")
    def publish_vk_text_only(call: CallbackQuery):
        """Пытается опубликовать с картинкой, если не получается - только текст"""
        chat_id = call.message.chat.id
        with store_lock:
            draft = user_drafts.get(chat_id)

        if not draft:
            bot.answer_callback_query(call.id, "❌ Нет черновика")
            return

        bot.answer_callback_query(call.id, "Публикуем в VK…")

        # Сначала пытаемся с картинкой
        try:
            post_id = vk_publish_with_image_required(VK_GROUP_ID, draft["image_bytes"], smart_vk_text(draft["text"]))
            url = vk_post_url(VK_GROUP_ID, post_id)
            bot.send_message(chat_id, f"✅ Опубликовано с картинкой: {url}")
            return
        except Exception as e:
            log.warning(f"VK post with image failed, trying text only: {e}")

        # Если не получилось с картинкой - публикуем только текст
        try:
            post_id = vk_publish_text(VK_GROUP_ID, smart_vk_text(draft["text"]))
            url = vk_post_url(VK_GROUP_ID, post_id)
            bot.send_message(chat_id, f"✅ Опубликовано (только текст): {url}")
            bot.send_message(chat_id, "⚠️ Картинка не загрузилась, опубликован только текст")
        except Exception as e:
            log.exception("VK text post error")
            bot.answer_callback_query(call.id, "❌ Ошибка публикации текста")
            bot.send_message(chat_id, f"❌ Ошибка публикации в VK: {e}")
