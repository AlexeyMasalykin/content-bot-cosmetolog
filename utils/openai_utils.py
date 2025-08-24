import requests
from config import OPENAI_API_KEY, OPENAI_MODEL_TEXT, OPENAI_MODEL_PROMPT
import logging

OPENAI_URL = "https://api.openai.com/v1/chat/completions"
HTTP_TIMEOUT = 30
log = logging.getLogger("tg-vk-bot")

def _openai_chat(messages, model: str) -> str:
    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model,
        "messages": messages,
    }
    r = requests.post(OPENAI_URL, headers=headers, json=payload, timeout=HTTP_TIMEOUT)
    try:
        data = r.json()
    except Exception as e:
        log.exception("OpenAI JSON error")
        raise RuntimeError(f"OpenAI ответ не JSON: {r.text[:500]}") from e

    if r.status_code >= 400 or "error" in data:
        raise RuntimeError(f"OpenAI ошибка: {data.get('error', data)}")

    return data["choices"][0]["message"]["content"].strip()

def generate_text(topic: str) -> str:
    prompt = (
        f"Ты — эксперт-косметолог и блогер. Генерируй посты для Telegram в стиле: понятно, дружелюбно, но с научными фактами.\n\n"
        f"ТЕМА: {topic}\n\n"
        f"Формат поста:\n"
        f"• Вступление-крючок (вопрос, миф, наблюдение)\n"
        f"• Основная часть — факты, советы или разбор (желательно в виде списков)\n"
        f"• Итог/вывод с мотивацией или ключевой мыслью\n\n"
        f"Правила:\n"
        f"• Используй подзаголовки: «Что это такое?», «Миф 1», «ТОП-5»\n"
        f"• Делай списки и структурированный текст для лёгкого восприятия\n"
        f"• Стиль — лёгкий, дружеский, но экспертный\n"
        f"• Объём: 1000–1500 знаков\n"
        f"• Объём: полный развернутый пост (без ограничений длины)\n"
        f"• Темы: уход за кожей, мифы и правда, процедуры, ингредиенты, здоровые привычки для кожи\n\n"
        f"Примеры фраз:\n"
        f"• Начало: «Давайте разберёмся, правда ли…»\n"
        f"• Конец: «Сияющая кожа — это система привычек, а не только косметика»\n\n"
        f"Напиши пост строго по этому формату:"
    )
    return _openai_chat([{"role": "user", "content": prompt}], OPENAI_MODEL_TEXT)

def generate_image_prompt(text: str) -> str:
    system_msg = (
        "Ты — помощник SMM-специалиста. На основе поста сформируй краткий промпт для генерации 1:1 изображения. "
        "Ключевые требования: чистый белый фон или нейтральный пастельный; минимализм; "
        "акцент на коже/уходе; без текста на изображении; без логотипов; как для Instagram."
    )
    return _openai_chat(
        [{"role": "system", "content": system_msg}, {"role": "user", "content": text}],
        OPENAI_MODEL_PROMPT
    )

def generate_topics() -> list[str]:
    """Генерирует 3 актуальные темы для постов на неделю"""
    prompt = (
        "Ты — эксперт-косметолог и блогер. "
        "Предложи 3 актуальные темы для постов на неделю в Telegram-канале о косметологии.\n\n"
        "Темы должны быть:\n"
        "• Сезонными и актуальными\n"
        "• Подходящими для формата: вступление-крючок → факты/советы → вывод\n"
        "• Разнообразными: уход за кожей, мифы и правда, процедуры, ингредиенты, здоровые привычки\n"
        "• Интересными для широкой аудитории\n"
        "• Подходящими для дружелюбного, но экспертного стиля\n\n"
        "Примеры хороших тем:\n"
        "• Правда ли, что кожа привыкает к косметике\n"
        "• Зимний уход: 5 главных правил\n"
        "• Витамин С для лица: мифы и факты\n\n"
        "Формат ответа: просто список из 3 тем, каждая с новой строки, без нумерации."
    )
    response = _openai_chat([{"role": "user", "content": prompt}], OPENAI_MODEL_TEXT)
    topics = [topic.strip() for topic in response.split('\n') if topic.strip()]
    return topics[:3]  # Берем только первые 3 темы

def edit_topics(topics: list[str], instruction: str) -> list[str]:
    """Редактирует темы согласно инструкции пользователя"""
    topics_text = '\n'.join(f"{i+1}. {topic}" for i, topic in enumerate(topics))
    prompt = (
        f"Отредактируй темы для постов согласно инструкции. "
        f"Сохрани профессиональный подход к косметологии.\n\n"
        f"ТЕКУЩИЕ ТЕМЫ:\n{topics_text}\n\n"
        f"ИНСТРУКЦИЯ:\n{instruction}\n\n"
        f"Верни 3 отредактированные темы, каждую с новой строки, без нумерации."
    )
    response = _openai_chat([{"role": "user", "content": prompt}], OPENAI_MODEL_TEXT)
    new_topics = [topic.strip() for topic in response.split('\n') if topic.strip()]
    return new_topics[:3]