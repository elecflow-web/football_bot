import os
import requests
import pandas as pd
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CallbackQueryHandler, CommandHandler, ContextTypes

ODDS_API_KEY = os.getenv("ODDS_API_KEY")
FOOTBALL_API_KEY = os.getenv("FOOTBALL_API_KEY")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")

BASE_ODDS_URL = "https://api.the-odds-api.com/v4/sports/soccer/odds/"
BASE_FOOTBALL_URL = "https://api.football-data.org/v4/matches/"

# Фильтры и лимиты
MAX_TOP_MATCHES = 10

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("Смотреть топ-матчи", callback_data='top_matches')],
        [InlineKeyboardButton("Отслеживать матч", callback_data='track_match')],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Привет! Выберите действие:", reply_markup=reply_markup)

def fetch_odds():
    params = {"apiKey": ODDS_API_KEY, "regions": "eu", "markets": "h2h,spreads,totals"}
    r = requests.get(BASE_ODDS_URL, params=params)
    r.raise_for_status()
    return r.json()

def fetch_matches():
    headers = {"X-Auth-Token": FOOTBALL_API_KEY}
    r = requests.get(BASE_FOOTBALL_URL, headers=headers)
    r.raise_for_status()
    return r.json().get("matches", [])

def analyze_match(match):
    # Простая оценка value: сравниваем xG с коэффициентами
    home_xg = match.get("homeTeam", {}).get("expectedGoals", 1.0)
    away_xg = match.get("awayTeam", {}).get("expectedGoals", 1.0)
    odds = match.get("odds", {"h2h":[2.0,3.0,3.5]})["h2h"]
    home_prob = home_xg / (home_xg + away_xg)
    value_home = home_prob * odds[0] - 1
    return {"match": match, "value_home": value_home}

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "top_matches":
        matches = fetch_matches()
        analyzed = [analyze_match(m) for m in matches]
        analyzed.sort(key=lambda x: x["value_home"], reverse=True)
        text = "Топ матчей по value:\n"
        for m in analyzed[:MAX_TOP_MATCHES]:
            home = m["match"]["homeTeam"]["name"]
            away = m["match"]["awayTeam"]["name"]
            val = round(m["value_home"],2)
            text += f"{home} vs {away} | Value: {val}\n"
        await query.edit_message_text(text=text)
    elif query.data == "track_match":
        await query.edit_message_text("Функция отслеживания матча пока в разработке.")

def main():
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.run_polling()

if __name__ == "__main__":
    main()
