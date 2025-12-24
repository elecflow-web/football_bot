import os
import requests
import pandas as pd
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes

# Получение ключей из переменных окружения
ODDS_API_KEY = os.getenv("ODDS_API_KEY")
FOOTBALL_API_KEY = os.getenv("FOOTBALL_API_KEY")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")

# Файл истории ставок
HISTORICAL_FILE = "history.csv"

# Загружаем историю ставок (если файл есть)
def load_history():
    if os.path.exists(HISTORICAL_FILE):
        return pd.read_csv(HISTORICAL_FILE, sep=";", parse_dates=["date"])
    else:
        df = pd.DataFrame(columns=["date","match","bet","odds","result"])
        df.to_csv(HISTORICAL_FILE, sep=";", index=False)
        return df

# Сохраняем ставку
def save_bet(match, bet, odds, result=""):
    df = load_history()
    df = df.append({"date": pd.Timestamp.now(), "match": match, "bet": bet, "odds": odds, "result": result}, ignore_index=True)
    df.to_csv(HISTORICAL_FILE, sep=";", index=False)

# Команда /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("Топ ставки", callback_data="topbets")],
        [InlineKeyboardButton("История", callback_data="history")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Выберите действие:", reply_markup=reply_markup)

# Callback для кнопок
async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data == "topbets":
        # Пример: подтягиваем топ-ставки из API (реально здесь нужно интегрировать API)
        keyboard = [
            [InlineKeyboardButton("1X Манчестер Сити", callback_data="bet_1x_mc")],
            [InlineKeyboardButton("Назад", callback_data="back")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text("Топ ставки:", reply_markup=reply_markup)
    elif query.data == "history":
        df = load_history()
        if df.empty:
            text = "История пуста"
        else:
            text = "\n".join([f"{row['date'].strftime('%Y-%m-%d %H:%M')} | {row['match']} | {row['bet']} | {row['odds']} | {row['result']}" for _, row in df.iterrows()])
        keyboard = [[InlineKeyboardButton("Назад", callback_data="back")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text, reply_markup=reply_markup)
    elif query.data.startswith("bet_"):
        # Сохраняем выбранную ставку
        save_bet(query.data[4:], query.data, odds=1.5)
        await query.edit_message_text(f"Ставка {query.data[4:]} сохранена!")
    elif query.data == "back":
        await start(update, context)

# Основная функция
def main():
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button))
    app.run_polling()

if __name__ == "__main__":
    main()
