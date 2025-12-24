import logging
import requests
import pandas as pd
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes, JobQueue

# Настройки
ODDS_API_KEY = "5f1e3adbb1e334788067c15ccc2e6978"
FOOTBALL_API_KEY = "afd3ed6b02202f71750b0cfcd0cacd5a"
TELEGRAM_TOKEN = "8033902386:AAFILhMFGnFuFU6l6LHWLk5wNxYHCze3Mx8"

# Файл истории
HISTORICAL_FILE = "history.csv"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Функция загрузки истории
def load_history():
    try:
        return pd.read_csv(HISTORICAL_FILE, sep=";", encoding="cp1251", parse_dates=["date"])
    except Exception:
        return pd.DataFrame(columns=["date", "match", "bet", "stake", "odds", "result"])

# Пример функции получения топ-ставок с API
def fetch_top_bets():
    url = f"https://api.the-odds-api.com/v4/sports/soccer_epl/odds/?apiKey={ODDS_API_KEY}&regions=eu&markets=h2h,spreads,totals"
    try:
        resp = requests.get(url, timeout=10)
        data = resp.json()
        bets = []
        for match in data[:5]:  # берем топ-5 матчей для примера
            bets.append({
                "match": f"{match['home_team']} vs {match['away_team']}",
                "odds": match['bookmakers'][0]['markets'][0]['outcomes'],
                "start_time": match['commence_time']
            })
        return bets
    except Exception as e:
        logger.error(f"Ошибка при получении топ-ставок: {e}")
        return []

# Функция уведомления топ-ставок
async def notify_top_bets(context: ContextTypes.DEFAULT_TYPE):
    chat_id = context.job.data["chat_id"]
    top_bets = fetch_top_bets()
    if not top_bets:
        await context.bot.send_message(chat_id=chat_id, text="Нет доступных топ-ставок.")
        return

    for bet in top_bets:
        text = f"Топ ставка:\n{bet['match']}\nНачало: {bet['start_time']}\nКоэффициенты: {bet['odds']}"
        await context.bot.send_message(chat_id=chat_id, text=text)

# Старт команды
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("Топ ставок", callback_data="topbets")],
        [InlineKeyboardButton("История", callback_data="history")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Привет! Выберите действие:", reply_markup=reply_markup)

# Обработка кнопок
async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data == "topbets":
        bets = fetch_top_bets()
        if not bets:
            await query.edit_message_text("Нет доступных топ-ставок.")
            return
        text = "\n\n".join([f"{b['match']} | {b['start_time']}" for b in bets])
        await query.edit_message_text(text=text)
    elif query.data == "history":
        df = load_history()
        if df.empty:
            await query.edit_message_text("История пуста.")
        else:
            text = "\n".join([f"{row['date']} | {row['match']} | {row['bet']} | {row['stake']} ₽ | {row['result']}" for i, row in df.iterrows()])
            await query.edit_message_text(text=text)

# Основная функция запуска бота
def main():
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button))

    # Настройка JobQueue для уведомлений каждые 10 минут
    if app.job_queue is None:
        import warnings
        warnings.warn("JobQueue не инициализирован. Установите PTB с [job-queue]")
    else:
        app.job_queue.run_repeating(notify_top_bets, interval=600, first=10, data={"chat_id": "YOUR_TELEGRAM_CHAT_ID"})

    app.run_polling()

if __name__ == "__main__":
    main()
