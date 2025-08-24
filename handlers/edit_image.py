# handlers/edit_image.py
from telebot.types import Message, CallbackQuery
from state import user_drafts, user_states, store_lock
from utils.openai_utils import _openai_chat
from utils.yandex_utils import generate_image_bytes_with_yc
from utils.tg_utils import action_keyboard, send_post_with_image


def register(bot):
    @bot.callback_query_handler(func=lambda c: c.data == "edit_image")
    def ask_image_edit(call: CallbackQuery):
        user_states[call.message.chat.id] = "waiting_image_hint"
        bot.send_message(
            call.message.chat.id, "Опишите желаемые изменения изображения (цвет, крупный план, объект и т.д.):"
        )


def apply_image_instruction(bot, msg: Message):
    user_id = msg.chat.id
    with store_lock:
        draft = user_drafts.get(user_id)

    if not draft:
        bot.send_message(user_id, "❌ Нет активного черновика.")
        user_states.pop(user_id, None)
        return

    wish = (msg.text or "").strip()
    prompt = (
        "Сформируй краткий промпт для генератора изображений (1:1) на основе текста поста и пожелания. "
        "Стиль минималистичный, без текста, фокус на теме ухода за кожей.\n\n"
        f"ПОСТ:\n{draft['text']}\n\nПОЖЕЛАНИЕ:\n{wish}"
    )

    try:
        new_prompt = _openai_chat([{"role": "user", "content": prompt}], "gpt-4o")
        new_bytes = generate_image_bytes_with_yc(new_prompt)
    except Exception as e:
        bot.send_message(user_id, f"❌ Не удалось обновить изображение: {e}")
        user_states.pop(user_id, None)
        return

    with store_lock:
        draft["image_bytes"] = new_bytes

    send_post_with_image(bot, user_id, draft["text"], new_bytes, reply_markup=action_keyboard())
    user_states.pop(user_id, None)
