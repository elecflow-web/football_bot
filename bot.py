import os
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, CallbackQueryHandler, JobQueue

# === Твои подключенные API ===
from my_apis import get_fixtures, get_odds, get_xg, elo_prob, LEAGUES, analyze_matches  # предполагаем твои функции

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

# ===== Обработчик /start =====
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("Топ ставки", callback_data="topbets")],
        [InlineKeyboardButton("Обновить", callback_data="refresh")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "Привет! Бот запущен и готов к работе.",
        reply_markup=reply_markup
    )

# ===== Асинхронный запуск анализа матчей =====
async def analyze_matches_async():
    # Запуск синхронного анализа в отдельном потоке
    bets = await asyncio.to_thread(analyze_matches)
    return bets

# ===== Обработчик кнопок =====
async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data == "topbets":
        await query.edit_message_text("Идёт анализ матчей, подождите...")
        bets = await analyze_matches_async()
        if not bets:
            await query.edit_message_text("Нет актуальных ставок.")
            return

        text = "💰 Топ ставки:\n\n"
        for b in bets[:12]:  # берем 12 лучших
            value, league, match, market, price = b
            text += f"{league} | {match} | {market} | Коэф: {price:.2f} | Value: {value:.2f}\n"
        await query.edit_message_text(text)

    elif query.data == "refresh":
        await query.edit_message_text("Обновление топ ставок…")
        bets = await analyze_matches_async()
        if bets:
            text = "🔄 Обновленные топ ставки:\n\n"
            for b in bets[:12]:
                value, league, match, market, price = b
                text += f"{league} | {match} | {market} | Коэф: {price:.2f} | Value: {value:.2f}\n"
            await query.edit_message_text(text)
        else:
            await query.edit_message_text("Нет новых ставок.")

# ===== Job для автоматической отправки топ ставок =====
async def scheduled_job(context: ContextTypes.DEFAULT_TYPE):
    bets = await analyze_matches_async()
    if TELEGRAM_CHAT_ID and bets:
        text = "💰 Автоматическое обновление топ ставок:\n\n"
        for b in bets[:12]:
            value, league, match, market, price = b
            text += f"{league} | {match} | {market} | Коэф: {price:.2f} | Value: {value:.2f}\n"
        await context.bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=text)

# ===== Основная функция =====
def main():
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    # Обработчики
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button))

    # JobQueue
    job_queue: JobQueue = app.job_queue
    job_queue.run_repeating(scheduled_job, interval=600, first=10)

    # Запуск бота
    app.run_polling()

if __name__ == "__main__":
    main()
