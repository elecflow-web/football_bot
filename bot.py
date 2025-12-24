import logging
import requests
import pandas as pd
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    JobQueue,
)

# -------------------
# Настройки
# -------------------
ODDS_API_KEY = "5f1e3adbb1e334788067c15ccc2e6978"
FOOTBALL_API_KEY = "afd3ed6b02202f71750b0cfcd0cacd5a"
TELEGRAM_TOKEN = "8033902386:AAFILhMFGnFuFU6l6LHWLk5wNxYHCze3Mx8"

# Включаем логирование
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)

# -------------------
# Функции для получения топ-ставок
# -------------------
def fetch_top_matches():
    """Получаем топовые матчи с API (пример)"""
    # Заглушка: здесь можно подключить ODDS API и FOOTBALL API
    return [
        {"match": "Manchester United vs Newcastle United", "start": "2025-12-26T20:00:00Z", "odds": 1.8},
        {"match": "Nottingham Forest vs Manchester City", "start": "2025-12-27T12:30:00Z", "odds": 2.1},
        {"match": "Arsenal vs Brighton and Hove Albion", "start": "2025-12-27T15:00:00Z", "odds": 1.95},
    ]


async def notify_top_bets(context: ContextTypes.DEFAULT_TYPE):
    """Рассылка топ-ставок"""
    chat_id = context.job.data["chat_id"]
    matches = fetch_top_matches()
    if not matches:
        await context.bot.send_message(chat_id=chat_id, text="Сейчас нет топовых ставок.")
        return

    for m in matches:
        text = f"Топ ставка:\n{m['match']}\nКоэффициент: {m['odds']}\nНачало: {m['start']}"
        keyboard = InlineKeyboardMarkup(
            [[
                InlineKeyboardButton("Отслеживать", callback_data=f"track|{m['match']}"),
                InlineKeyboardButton("Ставить", callback_data=f"bet|{m['match']}"),
            ]]
        )
        await context.bot.send_message(chat_id=chat_id, text=text, reply_markup=keyboard)

# -------------------
# Обработка кнопок
# -------------------
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    action, match = query.data.split("|")
    if action == "track":
        await query.edit_message_text(text=f"Вы начали отслеживать матч: {match}")
    elif action == "bet":
        await query.edit_message_text(text=f"Вы поставили на матч: {match}")


# -------------------
# Команды
# -------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = InlineKeyboardMarkup(
        [[InlineKeyboardButton("Показать топ-ставки", callback_data="show_top")]]
    )
    await update.message.reply_text("Привет! Выберите действие:", reply_markup=keyboard)


async def show_top(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await notify_top_bets(ContextTypes.DEFAULT_TYPE(job_queue=context.job_queue, job=None, bot=context.bot, chat_data=context.chat_data, user_data=context.user_data, data={"chat_id": update.effective_chat.id}))

# -------------------
# Основной запуск
# -------------------
def main():
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    # Обработчики
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler, pattern="track|.*|bet|.*"))
    
    # JobQueue: каждые 10 минут рассылаем топ-ставки
    app.job_queue.run_repeating(
        notify_top_bets, interval=600, first=10, data={"chat_id": "YOUR_TELEGRAM_CHAT_ID"}
    )

    # Запуск бота
    app.run_polling()

if __name__ == "__main__":
    main()
