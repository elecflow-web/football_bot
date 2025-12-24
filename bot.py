import os
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    ContextTypes,
    CommandHandler,
    CallbackQueryHandler,
)
from real_apis import analyze_matches  # твой полный API модуль

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[InlineKeyboardButton("Топ ставки сегодня", callback_data="top_bets")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "Привет! Нажми кнопку для получения топ-ставок сегодня.", reply_markup=reply_markup
    )

async def top_bets_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("Идёт анализ матчей, подождите...")

    loop = asyncio.get_event_loop()
    bets = await loop.run_in_executor(None, analyze_matches)

    if not bets:
        await query.edit_message_text("❌ Подходящих value-ставок не найдено.")
        return

    text = "🔥 Топ ставки сегодня:\n\n"
    for val, league, match, market, odd in bets:
        text += f"{league} | {match} | {market} | Коэф: {odd:.2f} | Value: {val:.2f}\n"

    await query.edit_message_text(text)

def main():
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(top_bets_callback, pattern="top_bets"))
    app.run_polling()

if __name__ == "__main__":
    main()
