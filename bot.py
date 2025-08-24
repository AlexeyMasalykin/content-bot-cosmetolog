import logging
import signal
import sys
from telebot import TeleBot
from config import BOT_TOKEN

from handlers import general, edit_text, edit_image, publish_telegram, publish_vk, content_planning, admin
from scheduler import init_scheduler
from state import save_state

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
log = logging.getLogger("tg-vk-bot")

bot = TeleBot(BOT_TOKEN)

# Инициализация планировщика
content_scheduler = init_scheduler(bot)

# Автоматический запуск планировщика при старте бота
log.info("Starting content scheduler automatically...")
content_scheduler.start_scheduler()
log.info("Content scheduler started successfully")

# Регистрация обработчиков (команды регистрируются первыми)
admin.register(bot)
content_planning.register(bot)
edit_text.register(bot)
edit_image.register(bot)
publish_telegram.register(bot)
publish_vk.register(bot)
general.register(bot)  # Общий обработчик текста должен быть последним


def signal_handler(signum, frame):
    """Обработчик сигналов для корректного завершения"""
    log.info("Received shutdown signal, stopping...")

    # Останавливаем планировщик
    if content_scheduler:
        content_scheduler.stop_scheduler()

    # Сохраняем состояние
    save_state()

    log.info("Bot stopped gracefully")
    sys.exit(0)


# Регистрируем обработчики сигналов
signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

if __name__ == "__main__":
    log.info("Bot started with content planning features")
    log.info("Use /admin to access admin panel")
    log.info("Use /start_scheduler to begin automatic scheduling")

    try:
        bot.polling(none_stop=True, interval=0, timeout=20)
    except KeyboardInterrupt:
        log.info("Bot stopped by user")
    except Exception as e:
        log.exception(f"Bot crashed: {e}")
    finally:
        # Сохраняем состояние при любом завершении
        save_state()
        if content_scheduler:
            content_scheduler.stop_scheduler()
