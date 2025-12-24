from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, CallbackQueryHandler, JobQueue
import os
import asyncio

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Привет! Бот запущен.")

async def notify_top_bets(context: ContextTypes.DEFAULT_TYPE):
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    if chat_id:
        await context.bot.send_message(chat_id=chat_id, text="Топ ставки обновлены!")

def main():
    # Создаём приложение с JobQueue
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    
    # Добавляем обработчики команд
    app.add_handler(CommandHandler("start", start))
    
    # Добавляем JobQueue вручную
    job_queue: JobQueue = app.job_queue
    job_queue.run_repeating(notify_top_bets, interval=600, first=10)
    
    # Запускаем бота
    app.run_polling()

if __name__ == "__main__":
    main()
