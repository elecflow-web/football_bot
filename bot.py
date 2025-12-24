import os
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    ContextTypes,
    CommandHandler,
    JobQueue,
)
import asyncio

# Получаем токен и chat_id из переменных окружения
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")  # id чата, куда отправлять уведомления

# Команда /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Привет! Бот запущен и готов к работе.")

# Job для отправки уведомлений о топ-ставках
async def notify_top_bets(context: ContextTypes.DEFAULT_TYPE):
    if TELEGRAM_CHAT_ID:
        await context.bot.send_message(chat_id=TELEGRAM_CHAT_ID, text="Топ ставки обновлены!")

# Главная функция
def main():
    # Создаём приложение
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    # Добавляем обработчики команд
    app.add_handler(CommandHandler("start", start))

    # Получаем JobQueue и добавляем повторяющийся job
    job_queue: JobQueue = app.job_queue
    job_queue.run_repeating(notify_top_bets, interval=600, first=10)  # каждые 10 минут

    # Запускаем бота
    app.run_polling()

if __name__ == "__main__":
    main()
