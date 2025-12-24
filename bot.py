import os
import asyncio
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
)

from my_apis import analyze_matches

TOKEN = os.environ.get("TELEGRAM_TOKEN")

# -----------------------------
# /start
# -----------------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("📊 Топ ставки сегодня", callback_data="analyze")],
    ]
    await update.message.reply_text(
        "Привет! Я анализирую матчи по коэффициентам и value.\n"
        "Нажми кнопку ниже 👇",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )

# -----------------------------
# Callback handler
# -----------------------------
async def callbacks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "analyze":
        await query.edit_message_text("⏳ Идёт анализ матчей, подождите...")

        # ⚠️ КЛЮЧЕВОЙ МОМЕНТ — чтобы НЕ ВИСЛО
        loop = asyncio.get_running_loop()
        bets = await loop.run_in_executor(None, analyze_matches)

        if not bets:
            await query.edit_message_text("❌ Подходящих value-ставок не найдено.")
            return

        text = "🔥 *ТОП VALUE-СТАВКИ*\n\n"
        for i, (value, league, match, market, odds) in enumerate(bets, 1):
            text += (
                f"{i}. *{match}*\n"
                f"Лига: {league}\n"
                f"Рынок: {market}\n"
                f"Коэфф: {odds}\n"
                f"Value: {value:.2f}\n\n"
            )

        await query.edit_message_text(text, parse_mode="Markdown")

# -----------------------------
# MAIN
# -----------------------------
def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(callbacks))

    print("BOT STARTED")
    app.run_polling()

if __name__ == "__main__":
    main()
