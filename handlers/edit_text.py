# handlers/edit_text.py
from telebot.types import Message, CallbackQuery
from state import user_drafts, store_lock, user_states
from utils.openai_utils import _openai_chat
from utils.tg_utils import action_keyboard, send_post_with_image


def register(bot):
    @bot.callback_query_handler(func=lambda c: c.data == "edit_text")
    def ask_edit(call: CallbackQuery):
        user_states[call.message.chat.id] = "waiting_edit_hint"
        bot.send_message(call.message.chat.id, "Опишите, как изменить текст (стиль, объём, акценты):")


def apply_edit_instruction(bot, msg: Message):
    user_id = msg.chat.id
    with store_lock:
        draft = user_drafts.get(user_id)

    if not draft:
        bot.send_message(user_id, "❌ Нет активного черновика.")
        user_states.pop(user_id, None)
        return

    prompt = (
        "Отредактируй текст строго по инструкции. Сохрани факты, улучшай структуру и ясность. "
        "Верни только готовый текст без пояснений.\n\n"
        f"ТЕКСТ:\n{draft['text']}\n\nИНСТРУКЦИЯ:\n{(msg.text or '').strip()}"
    )
    try:
        new_text = _openai_chat([{"role": "user", "content": prompt}], "gpt-4o")
    except Exception as e:
        bot.send_message(user_id, f"❌ Не получилось отредактировать: {e}")
        user_states.pop(user_id, None)
        return

    with store_lock:
        draft["text"] = new_text

    send_post_with_image(bot, user_id, new_text, draft["image_bytes"], reply_markup=action_keyboard())
    user_states.pop(user_id, None)
