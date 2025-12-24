import os
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CallbackQueryHandler, CommandHandler, ContextTypes

ODDS_API_KEY = os.getenv("ODDS_API_KEY")
FOOTBALL_API_KEY = os.getenv("FOOTBALL_API_KEY")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("Смотреть топ-матчи", callback_data='top_matches')],
        [InlineKeyboardButton("Отслеживать матч", callback_data='track_match')],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Привет! Выберите действие:", reply_markup=reply_markup)

def fetch_dummy_matches():
    # Пока для теста возвращаем фиктивные данные, чтобы кнопки работали
    return [
        {"home": "Manchester City", "away": "Liverpool", "value": 0.15},
        {"home": "Real Madrid", "away": "Barcelona", "value": 0.12},
    ]

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data == "top_matches":
        matches = fetch_dummy_matches()
        if not matches:
            await query.edit_message_text("Нет доступных матчей.")
            return
        text = "Топ матчей по value:\n"
        for m in matches:
            text += f"{m['home']} vs {m['away']} | Value: {m['value']}\n"
        await query.edit_message_text(text=text)
    
    elif query.data == "track_match":
        await query.edit_message_text("Функция отслеживания матча пока в разработке.")

def main():
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.run_polling()

if __name__ == "__main__":
    main()
