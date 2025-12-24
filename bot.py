import os
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CallbackQueryHandler, CommandHandler, ContextTypes

ODDS_API_KEY = os.getenv("ODDS_API_KEY")
FOOTBALL_API_KEY = os.getenv("FOOTBALL_API_KEY")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")

# Список отслеживаемых матчей (в памяти, можно заменить на базу)
tracked_matches = []

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("Смотреть топ-матчи", callback_data='top_matches')],
        [InlineKeyboardButton("Отслеживать матч", callback_data='track_match')],
        [InlineKeyboardButton("Мои отслеживаемые ставки", callback_data='my_tracked')],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Привет! Выберите действие:", reply_markup=reply_markup)

def fetch_matches():
    # Получаем список матчей с букмекеров через ODDS API
    url = f"https://api.the-odds-api.com/v4/sports/soccer_epl/odds?apiKey={ODDS_API_KEY}&regions=eu&markets=h2h,spreads,totals"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        matches = []
        for match in data:
            # Берем первую букмекерскую линию для упрощения
            if not match.get("bookmakers"):
                continue
            odds = match["bookmakers"][0]["markets"]
            matches.append({
                "home": match["home_team"],
                "away": match["away_team"],
                "odds": odds,
                "commence_time": match.get("commence_time"),
            })
        return matches
    except Exception as e:
        print("Error fetching matches:", e)
        return []

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data == "top_matches":
        matches = fetch_matches()
        if not matches:
            await query.edit_message_text("Нет доступных матчей на данный момент.")
            return
        keyboard = []
        text = "Топ матчей по доступным коэффициентам:\n"
        for i, m in enumerate(matches[:10]):
            text += f"{m['home']} vs {m['away']} | Начало: {m['commence_time']}\n"
            keyboard.append([InlineKeyboardButton(f"Отслеживать {m['home']} vs {m['away']}", callback_data=f"track_{i}")])
        keyboard.append([InlineKeyboardButton("Назад", callback_data="back")])
        await query.edit_message_text(text=text, reply_markup=InlineKeyboardMarkup(keyboard))

    elif query.data.startswith("track_"):
        idx = int(query.data.split("_")[1])
        matches = fetch_matches()
        if idx < len(matches):
            tracked_matches.append(matches[idx])
            await query.edit_message_text(f"Вы начали отслеживать матч {matches[idx]['home']} vs {matches[idx]['away']}")
        else:
            await query.edit_message_text("Ошибка: матч не найден.")
    
    elif query.data == "track_match":
        await query.edit_message_text("Выберите матч через 'Смотреть топ-матчи', чтобы начать отслеживание.")

    elif query.data == "my_tracked":
        if not tracked_matches:
            await query.edit_message_text("Вы пока не отслеживаете ни один матч.")
            return
        text = "Ваши отслеживаемые матчи:\n"
        for m in tracked_matches:
            text += f"{m['home']} vs {m['away']} | Начало: {m['commence_time']}\n"
        await query.edit_message_text(text)

    elif query.data == "back":
        await start(update, context)

def main():
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.run_polling()

if __name__ == "__main__":
    main()
