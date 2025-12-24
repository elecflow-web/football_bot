import logging
import requests
import pandas as pd
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes, JobQueue

# ==================== НАСТРОЙКИ ====================
ODDS_API_KEY = "5f1e3adbb1e334788067c15ccc2e6978"
FOOTBALL_API_KEY = "afd3ed6b02202f71750b0cfcd0cacd5a"
TELEGRAM_TOKEN = "8033902386:AAFILhMFGnFuFU6l6LHWLk5wNxYHCze3Mx8"
CHAT_ID = "YOUR_TELEGRAM_CHAT_ID"  # <- сюда вставь свой ID или чат

MAX_BETS = 5  # Сколько топ ставок показывать
# =====================================================

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ======== Функции работы с API ========
def get_upcoming_matches():
    url = f"https://api.football-data.org/v2/matches"
    headers = {"X-Auth-Token": FOOTBALL_API_KEY}
    resp = requests.get(url, headers=headers)
    if resp.status_code != 200:
        return []
    data = resp.json()
    matches = []
    for m in data.get("matches", []):
        matches.append({
            "home": m["homeTeam"]["name"],
            "away": m["awayTeam"]["name"],
            "date": m["utcDate"]
        })
    return matches

def get_top_bets():
    url = f"https://api.the-odds-api.com/v4/sports/soccer/odds"
    params = {"apiKey": ODDS_API_KEY, "regions": "eu", "markets": "h2h,spreads,totals"}
    resp = requests.get(url, params=params)
    if resp.status_code != 200:
        return []
    data = resp.json()
    candidates = []
    for event in data:
        for bookmaker in event.get("bookmakers", []):
            for market in bookmaker.get("markets", []):
                for outcome in market.get("outcomes", []):
                    candidates.append({
                        "match": f"{event['home_team']} vs {event['away_team']}",
                        "market": market["key"],
                        "selection": outcome["name"],
                        "odds": outcome["price"]
                    })
    return pd.DataFrame(candidates).sort_values("odds", ascending=False).head(MAX_BETS).to_dict('records')

# ======== Телеграм функции ========
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("Топ ставок", callback_data="topbets")],
        [InlineKeyboardButton("Топ матчей", callback_data="topmatches")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Привет! Выберите действие:", reply_markup=reply_markup)

async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data == "topbets":
        bets = get_top_bets()
        if not bets:
            text = "Нет ставок по фильтрам."
        else:
            text = "Топ ставок:\n"
            for b in bets:
                text += f"{b['match']} | {b['market']} | {b['selection']} | {b['odds']}\n"
        await query.edit_message_text(text)
    elif query.data == "topmatches":
        matches = get_upcoming_matches()
        if not matches:
            text = "Нет матчей."
        else:
            text = "Топ матчей:\n"
            for m in matches[:MAX_BETS]:
                text += f"{m['home']} vs {m['away']} | Начало: {m['date']}\n"
        await query.edit_message_text(text)

# ======== Уведомления (JobQueue) ========
async def notify_top_bets(context: ContextTypes.DEFAULT_TYPE):
    bets = get_top_bets()
    if not bets:
        return
    text = "🔥 Новые топ ставки:\n"
    for b in bets:
        text += f"{b['match']} | {b['market']} | {b['selection']} | {b['odds']}\n"
    await context.bot.send_message(chat_id=CHAT_ID, text=text)

# ======== Запуск приложения ========
if __name__ == "__main__":
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    # Handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button))

    # JobQueue
    job_queue: JobQueue = app.job_queue
    job_queue.run_repeating(notify_top_bets, interval=600, first=10)

    # Start
    app.run_polling()
