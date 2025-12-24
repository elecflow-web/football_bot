from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes, JobQueue
import asyncio

TELEGRAM_TOKEN = "YOUR_TELEGRAM_TOKEN_HERE"

# --- Функции бота ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("Топ матчи", callback_data='top_matches')],
        [InlineKeyboardButton("Отслеживать матч", callback_data='track_match')],
        [InlineKeyboardButton("Ставки", callback_data='bet')],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Привет! Выберите действие:", reply_markup=reply_markup)

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data == "top_matches":
        await query.edit_message_text("Топ матчей:\n1. Манчестер Юн vs Ньюкасл\n2. Арсенал vs Брайтон\n... (пример)")
    elif query.data == "track_match":
        await query.edit_message_text("Вы начали отслеживание матча.")
    elif query.data == "bet":
        await query.edit_message_text("Вы выбрали ставку.")
    
    # Кнопка назад
    keyboard = [[InlineKeyboardButton("Назад", callback_data='back')]]
    await query.message.reply_text("Меню:", reply_markup=InlineKeyboardMarkup(keyboard))

async def back(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await start(update, context)

# --- Повторяющаяся задача ---
async def notify_top_bets(context: ContextTypes.DEFAULT_TYPE):
    chat_id = context.job.data["chat_id"]
    await context.bot.send_message(chat_id=chat_id, text="Топ ставки обновлены!")

# --- Главная функция ---
async def main():
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    
    # Обработчики команд и кнопок
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler, pattern="^(top_matches|track_match|bet)$"))
    app.add_handler(CallbackQueryHandler(back, pattern="^back$"))
    
    # JobQueue — уведомления каждые 10 минут
    job_queue: JobQueue = app.job_queue
    job_queue.run_repeating(notify_top_bets, interval=600, first=10, data={"chat_id": "YOUR_TELEGRAM_CHAT_ID"})
    
    # Запуск бота
    await app.run_polling()

if __name__ == "__main__":
    asyncio.run(main())
