# handlers/publish_telegram.py
from telebot.types import CallbackQuery
from config import TELEGRAM_CHANNEL_ID
from state import user_drafts, store_lock
from utils.tg_utils import truncate_caption, send_post_with_image
import io
import logging

log = logging.getLogger("tg-vk-bot")

def register(bot):
    @bot.callback_query_handler(func=lambda c: c.data == "publish_post")
    def publish_to_channel(call: CallbackQuery):
        chat_id = call.message.chat.id
        with store_lock:
            draft = user_drafts.get(chat_id)

        if not draft:
            bot.answer_callback_query(call.id, "❌ Нет черновика")
            return

        try:
            # Для каналов используем полный текст без обрезки, очищенный от Markdown
            from utils.tg_utils import clean_markdown
            send_post_with_image(
                bot,
                TELEGRAM_CHANNEL_ID,
                clean_markdown(draft["text"]),
                draft["image_bytes"]
            )
        except Exception as e:
            log.exception("Ошибка публикации в канал")
            bot.answer_callback_query(call.id, "❌ Ошибка публикации в Telegram")
            bot.send_message(chat_id, f"Ошибка: {e}")
            return

        bot.answer_callback_query(call.id, "✅ Опубликовано в Telegram")
        bot.send_message(chat_id, "Готово: пост отправлен в канал.")