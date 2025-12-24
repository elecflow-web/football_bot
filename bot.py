import os
import asyncio
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
)

TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")  # можно не указывать

# ---------- COMMANDS ----------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 Бот запущен.\n"
        "Топовые ставки приходят автоматически."
    )

# ---------- ANALYTICS ----------

def analyze():
    # ⚠️ здесь твоя реальная аналитика (xG, Elo, Odds API)
    return [
        "⚽ Arsenal vs Brighton\n"
        "➡️ Over 2.5 @1.92\n"
        "📈 Value: +11%\n"
        "🎯 Вероятность: 63%"
    ]

# ---------- JOB ----------

async def notify_top_bets(context: ContextTypes.DEFAULT_TYPE):
    bets = analyze()
    if not bets:
        return

    text = "🔥 ТОП СТАВКИ:\n\n" + "\n\n".join(bets)

    if CHAT_ID:
        await context.bot.send_message(chat_id=CHAT_ID, text=text)

# ---------- MAIN ----------

def main():
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    app.add_handler(CommandHandler("start", start))

    # ✅ JobQueue ГАРАНТИРОВАННО есть (из-за [job-queue])
    app.job_queue.run_repeating(
        notify_top_bets,
        interval=900,   # каждые 15 минут
        first=10
    )

    print("BOT STARTED")
    app.run_polling()

if __name__ == "__main__":
    main()
