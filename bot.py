import os
import logging
import requests
import pandas as pd
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes

# --- Настройки ---
ODDS_API_KEY = os.getenv("ODDS_API_KEY", "5f1e3adbb1e334788067c15ccc2e6978")
FOOTBALL_API_KEY = os.getenv("FOOTBALL_API_KEY", "afd3ed6b02202f71750b0cfcd0cacd5a")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "8033902386:AAFILhMFGnFuFU6l6LHWLk5wNxYHCze3Mx8")
CHAT_ID = os.getenv("YOUR_TELEGRAM_CHAT_ID", "")

MAX_BETS = 5

# --- Логирование ---
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# --- Функции работы с API ---
def fetch_top_matches():
    """Возвращает топ матчей с коэффициентами"""
    url = f"https://api.the-odds-api.com/v4/sports/soccer_epl/odds/?apiKey={ODDS_API_KEY}&regions=eu&markets=h2h,spreads,totals"
    try:
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        logger.error(f"Ошибка при получении данных: {e}")
        return []

def analyze_matches(matches):
    """Простейший анализ: выбираем топ MAX_BETS по value"""
    candidates = []
    for match in matches:
        try:
            home_team = match["home_team"]
            away_team = match["away_team"]
            commence_time = match["commence_time"]
            for bookmaker in match.get("bookmakers", []):
                for market in bookmaker.get("markets", []):
                    if market["key"] == "h2h":
                        outcomes = market["outcomes"]
                        for outcome in outcomes:
                            value = float(outcome.get("price", 0))
                            candidates.append({
                                "match": f"{home_team} vs {away_team}",
                                "start": commence_time,
                                "team": outcome["name"],
                                "odds": value
                            })
        except Exception as e:
            logger.warning(f"Ошибка анализа матча: {e}")
    df = pd.DataFrame(candidates)
    if not df.empty:
        df = df.sort_values("odds", ascending=False).head(MAX_BETS)
    return df.to_dict("records")

# --- Telegram Handlers ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("Топ матчей", callback_data="top_matches")],
        [InlineKeyboardButton("Отслеживать ставки", callback_data="track_bets")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Привет! Выберите действие:", reply_markup=reply_markup)

async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data == "top_matches":
        matches = fetch_top_matches()
        analyzed = analyze_matches(matches)
        if analyzed:
            text = "Топовые ставки:\n\n"
            for bet in analyzed:
                text += f"{bet['match']} | Ставка: {bet['team']} | Коэффициент: {bet['odds']}\n"
        else:
            text = "Нет доступных ставок."
        await query.edit_message_text(text)
    
    elif query.data == "track_bets":
        await query.edit_message_text("Здесь будут отслеживаемые ставки. Пока пусто.")

# --- Push уведомления по таймеру ---
async def notify_top_bets(context: ContextTypes.DEFAULT_TYPE):
    matches = fetch_top_matches()
    analyzed = analyze_matches(matches)
    if analyzed and CHAT_ID:
        text = "🔔 Новые топовые ставки:\n\n"
        for bet in analyzed:
            text += f"{bet['match']} | Ставка: {bet['team']} | Коэффициент: {bet['odds']}\n"
        await context.bot.send_message(chat_id=CHAT_ID, text=text)

# --- Основная функция ---
def main():
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    # Команды
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button))

    # JobQueue для push уведомлений каждые 10 минут
    if app.job_queue:
        app.job_queue.run_repeating(notify_top_bets, interval=600, first=10)

    app.run_polling()

if __name__ == "__main__":
    main()
