import os
import requests
import pandas as pd
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes, JobQueue
from datetime import datetime, timedelta

ODDS_API_KEY = os.getenv("ODDS_API_KEY")
FOOTBALL_API_KEY = os.getenv("FOOTBALL_API_KEY")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
STAKES_FILE = "stakes.csv"

if not os.path.exists(STAKES_FILE):
    pd.DataFrame(columns=["match", "market", "bet", "stake", "odds", "datetime", "status"]).to_csv(STAKES_FILE, index=False, sep=";")

# =======================================
# Получение матчей и коэффициентов
# =======================================
def get_upcoming_matches():
    url = f"https://api.the-odds-api.com/v4/sports/soccer_epl/odds/?apiKey={ODDS_API_KEY}&regions=eu&markets=h2h,spreads,totals"
    try:
        resp = requests.get(url)
        if resp.status_code == 200:
            return resp.json()
        return []
    except:
        return []

# =======================================
# Анализ матчей, вычисление value
# =======================================
def analyze_match(match):
    best_bets = []
    match_name = f"{match['home_team']} vs {match['away_team']}"
    for bookmaker in match['bookmakers']:
        for market in bookmaker['markets']:
            for outcome in market['outcomes']:
                implied_prob = 1 / outcome['price']
                value = 0.05
                if implied_prob < (1 - value):
                    best_bets.append({
                        "match": match_name,
                        "market": market['key'],
                        "bet": outcome['name'],
                        "odds": outcome['price'],
                        "value": value
                    })
    best_bets = sorted(best_bets, key=lambda x: x['value'], reverse=True)
    return best_bets[:5]

# =======================================
# Telegram: Главное меню
# =======================================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("Топ ставки", callback_data='top')],
        [InlineKeyboardButton("Мои ставки", callback_data='mybets')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Привет! Выберите действие:", reply_markup=reply_markup)

# =======================================
# Кнопки меню и действия
# =======================================
async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "top":
        matches = get_upcoming_matches()
        if not matches:
            await query.edit_message_text("Нет доступных матчей.")
            return
        message = "Топ ставки:\n"
        buttons = []
        for m in matches[:10]:
            bets = analyze_match(m)
            for b in bets:
                message += f"{b['match']} | {b['market']} | {b['bet']} | Коэф: {b['odds']}\n"
                buttons.append([InlineKeyboardButton(f"Отслеживать {b['bet']}", callback_data=f"track|{b['match']}|{b['market']}|{b['bet']}|{b['odds']}")])
        buttons.append([InlineKeyboardButton("Назад", callback_data="back")])
        reply_markup = InlineKeyboardMarkup(buttons)
        await query.edit_message_text(message, reply_markup=reply_markup)

    elif data.startswith("track|"):
        _, match_name, market, bet, odds = data.split("|")
        df = pd.read_csv(STAKES_FILE, sep=";")
        df = pd.concat([df, pd.DataFrame([{
            "match": match_name, "market": market, "bet": bet, "stake": 0,
            "odds": float(odds), "datetime": datetime.now(), "status": "tracking"
        }])], ignore_index=True)
        df.to_csv(STAKES_FILE, sep=";", index=False)
        await query.edit_message_text(f"Ставка {bet} на матч {match_name} теперь отслеживается.")

    elif data == "mybets":
        df = pd.read_csv(STAKES_FILE, sep=";")
        if df.empty:
            await query.edit_message_text("Нет сохраненных ставок.")
            return
        message = "Ваши ставки:\n"
        for _, row in df.iterrows():
            message += f"{row['match']} | {row['market']} | {row['bet']} | Статус: {row['status']}\n"
        buttons = [[InlineKeyboardButton("Назад", callback_data="back")]]
        reply_markup = InlineKeyboardMarkup(buttons)
        await query.edit_message_text(message, reply_markup=reply_markup)

    elif data == "back":
        await start(update, context)

# =======================================
# Авто-обновление топ-ставок
# =======================================
async def notify_top_bets(context: ContextTypes.DEFAULT_TYPE):
    matches = get_upcoming_matches()
    top_bets = []
    for m in matches[:10]:
        top_bets.extend(analyze_match(m))
    df = pd.read_csv(STAKES_FILE, sep=";")
    for bet in top_bets:
        if not ((df['match'] == bet['match']) & (df['market'] == bet['market']) & (df['bet'] == bet['bet'])).any():
            # Push уведомление
            chat_id = context.job.data["chat_id"]
            await context.bot.send_message(chat_id, text=f"Новая топ-ставка:\n{bet['match']} | {bet['market']} | {bet['bet']} | Коэф: {bet['odds']}")
            # Сохраняем в файл как отслеживаемую
            df = pd.concat([df, pd.DataFrame([{
                "match": bet['match'], "market": bet['market'], "bet": bet['bet'],
                "stake": 0, "odds": bet['odds'], "datetime": datetime.now(), "status": "tracking"
            }])], ignore_index=True)
            df.to_csv(STAKES_FILE, sep=";", index=False)

# =======================================
# Запуск приложения
# =======================================
if __name__ == "__main__":
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button))

    # Планировщик авто-уведомлений
    job_queue: JobQueue = app.job_queue
    job_queue.run_repeating(notify_top_bets, interval=600, first=10, data={"chat_id": "YOUR_TELEGRAM_CHAT_ID"})

    print("Бот запущен...")
    app.run_polling()
